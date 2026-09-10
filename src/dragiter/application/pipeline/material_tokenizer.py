# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Michael Buchold

import logging
import re

from dragiter.application.core.xdi import Worker
from dragiter.domain.models.material import Chunk, Material
from dragiter.domain.models.parameters import ExecutionParameters
from dragiter.domain.models.resources import Resources, ResourceSection
from dragiter.domain.ports.text_file_reader import TextFileReader

logger = logging.getLogger(__name__)


class MaterialTokenizer(Worker):
    # Default cap when max_chunks is unset. Prevents combinatorial explosion.
    DEFAULT_MAX_CHUNKS: int = 200
    MAX_TOTAL_CHUNKS: int = DEFAULT_MAX_CHUNKS
    # Warning threshold for undersized final chunks (in characters)
    WARN_MIN_CHARS: int = 50
    _PACK_SEP = "\n\n"

    def __init__(self, text_file_reader: TextFileReader) -> None:
        self.text_file_reader = text_file_reader

    def run(self, resources: Resources, ep: ExecutionParameters) -> Material:
        all_chunks: list[Chunk] = []

        try:
            for resource_section in resources.resource_sections:
                all_chunks.extend(self._process_markdown_configs(resource_section, ep))

                # --- CIRCUIT BREAKER ---
                limit = self._max_chunks(ep)
                if len(all_chunks) > limit:
                    raise MaterialTokenizerError(
                        f"Generated {len(all_chunks)} chunks, which exceeds the limit of {limit} "
                        f"(max_chunks). Refine the regex patterns, process fewer files, or raise "
                        f"--max-chunks."
                    )

            return Material(chunks=all_chunks)

        except MaterialTokenizerError:
            raise  # preserve the specific, actionable message

        except Exception as e:
            raise MaterialTokenizerError("Failed to create chunks.") from e

    def _process_markdown_configs(self, rs: ResourceSection, ep: ExecutionParameters) -> list[Chunk]:
        section_chunks: list[Chunk] = []
        global_id: int = 1
        limit = self._effective_limit(ep, rs)
        compiled_patterns = self._compile_patterns(rs)
        if ep.pack_limit_chars_int_setting.is_set:
            limit_origin = "global"
        elif rs.pack_limit_chars is not None and rs.pack_limit_chars > 0:
            limit_origin = "section"
        else:
            limit_origin = "off"
        logger.debug(
            f"Section '{rs.section_name}': {len(rs.file_paths)} file(s), "
            f"{len(compiled_patterns)} pattern(s), "
            f"pack_limit_chars={limit if limit is not None else 'off'} ({limit_origin})"
        )

        for path_obj in rs.file_paths:
            filename = path_obj.path.name
            source = f"{rs.section_name}:{filename}"
            content = self.text_file_reader.read(path_obj)
            logger.debug(f"{source}: read {len(content)} chars")
            pieces = self._split_staged(content, compiled_patterns, limit, source=source)
            file_chunks: list[Chunk] = []

            for piece in pieces:
                file_chunks.append(
                    Chunk(
                        num_id=0,
                        filename=path_obj.path.as_posix(),
                        section_name=rs.section_name,
                        section_num_id=0,
                        valid=self._is_content_valid(piece, rs.exclude_filters, rs.include_filters),
                        content=piece,
                    )
                )

            valid_count = sum(1 for chunk in file_chunks if chunk.valid)
            logger.debug(
                f"{source}: {len(file_chunks)} piece(s) after split, "
                f"{valid_count} valid, {len(file_chunks) - valid_count} invalid"
            )

            if limit is not None:
                file_chunks = self._pack_file_chunks(file_chunks, limit, source=source)

            self._log_final_file_chunks(file_chunks, filename, rs.section_name, limit)

            section_internal_id = 1
            for chunk in file_chunks:
                chunk.num_id = global_id
                chunk.section_num_id = section_internal_id
                section_chunks.append(chunk)
                global_id += 1
                section_internal_id += 1

        return section_chunks

    def _compile_patterns(self, rs: ResourceSection) -> list[re.Pattern[str]]:
        compiled: list[re.Pattern[str]] = []
        for index, pattern in enumerate(rs.regex_patterns):
            try:
                compiled.append(re.compile(pattern, flags=re.MULTILINE))
            except re.error as exc:
                raise MaterialTokenizerError(
                    f"Invalid regex_patterns[{index}] in section '{rs.section_name}': {exc}"
                ) from exc
        return compiled

    def _split_staged(
        self,
        text: str,
        patterns: list[re.Pattern[str]],
        limit: int | None,
        *,
        source: str,
    ) -> list[str]:
        """Split *text* with pattern 0, then refine oversized pieces with the rest.

        Later patterns run only when a character budget is set and a piece still
        exceeds it. Capturing groups are ignored; cuts are match-start positions.
        """
        if not patterns:
            stripped = text.strip()
            return [stripped] if stripped else []

        pieces = self._split_on_regex(text, patterns[0])
        logger.debug(
            f"{source}: primary pattern 1/{len(patterns)} on {len(text)} chars "
            f"-> {len(pieces)} piece(s)"
        )
        if limit is None or len(patterns) == 1:
            return pieces

        refined: list[str] = []
        for piece in pieces:
            refined.extend(
                self._refine_overflow(
                    piece,
                    patterns[1:],
                    limit,
                    source=source,
                    pattern_index=2,
                    total_patterns=len(patterns),
                )
            )
        logger.debug(f"{source}: {len(refined)} piece(s) after overflow refine")
        return refined

    def _refine_overflow(
        self,
        text: str,
        patterns: list[re.Pattern[str]],
        limit: int,
        *,
        source: str,
        pattern_index: int,
        total_patterns: int,
    ) -> list[str]:
        if len(text) <= limit or not patterns:
            return [text]

        split_parts = self._split_on_regex(text, patterns[0])
        rest = patterns[1:]
        logger.debug(
            f"{source}: pattern {pattern_index}/{total_patterns} on {len(text)} chars "
            f"-> {len(split_parts)} piece(s)"
        )
        if split_parts == [text]:
            logger.debug(
                f"{source}: pattern {pattern_index}/{total_patterns} had no effect"
            )
            return self._refine_overflow(
                text,
                rest,
                limit,
                source=source,
                pattern_index=pattern_index + 1,
                total_patterns=total_patterns,
            )

        refined: list[str] = []
        for part in split_parts:
            if len(part) > limit and rest:
                refined.extend(
                    self._refine_overflow(
                        part,
                        rest,
                        limit,
                        source=source,
                        pattern_index=pattern_index + 1,
                        total_patterns=total_patterns,
                    )
                )
            else:
                refined.append(part)
        return refined

    @staticmethod
    def _split_on_regex(text: str, compiled: re.Pattern[str]) -> list[str]:
        """Cut *text* at each match start. The match text stays in the following piece."""
        if not text:
            return []

        starts: list[int] = []
        last_start = -1
        for match in compiled.finditer(text):
            start = match.start()
            if start == last_start:
                continue
            starts.append(start)
            last_start = start

        if not starts:
            stripped = text.strip()
            return [stripped] if stripped else []

        bounds: list[int] = []
        if starts[0] != 0:
            bounds.append(0)
        bounds.extend(starts)
        bounds.append(len(text))

        pieces: list[str] = []
        for index in range(len(bounds) - 1):
            if bounds[index] == bounds[index + 1]:
                continue
            piece = text[bounds[index]:bounds[index + 1]].strip()
            if piece:
                pieces.append(piece)
        return pieces

    def _effective_limit(self, ep: ExecutionParameters, rs: ResourceSection) -> int | None:
        if ep.pack_limit_chars_int_setting.is_set:
            value = ep.pack_limit_chars_int_setting.value
            if value <= 0:
                return None
            return value
        section_value = rs.pack_limit_chars
        if section_value is None or section_value <= 0:
            return None
        return section_value

    def _pack_file_chunks(
        self, chunks: list[Chunk], limit: int, *, source: str
    ) -> list[Chunk]:
        if len(chunks) <= 1:
            logger.debug(f"{source}: pack skipped ({len(chunks)} chunk(s))")
            return chunks
        forward = self._greedy_pack(chunks, limit)
        backward = self._greedy_pack_backward(chunks, limit)
        chosen = self._choose_pack(forward, backward)
        direction = "backward" if chosen is backward else "forward"
        logger.debug(
            f"{source}: pack {len(chunks)} chunk(s) -> "
            f"forward={len(forward)} backward={len(backward)} chosen={direction}"
        )
        return chosen

    def _greedy_pack(self, chunks: list[Chunk], limit: int) -> list[Chunk]:
        packs: list[list[Chunk]] = []
        current = [chunks[0]]
        current_len = len(chunks[0].content)
        for chunk in chunks[1:]:
            extra = len(self._PACK_SEP) + len(chunk.content)
            if chunk.valid == current[0].valid and current_len + extra <= limit:
                current.append(chunk)
                current_len += extra
            else:
                packs.append(current)
                current = [chunk]
                current_len = len(chunk.content)
        packs.append(current)
        return [self._combine_pack(pack) for pack in packs]

    def _greedy_pack_backward(self, chunks: list[Chunk], limit: int) -> list[Chunk]:
        packs_rev: list[list[Chunk]] = []
        i = len(chunks) - 1
        while i >= 0:
            start = i
            current_len = len(chunks[i].content)
            j = i - 1
            while j >= 0:
                extra = len(self._PACK_SEP) + len(chunks[j].content)
                if chunks[j].valid == chunks[i].valid and current_len + extra <= limit:
                    current_len += extra
                    start = j
                    j -= 1
                else:
                    break
            packs_rev.append(chunks[start:i + 1])
            i = start - 1
        packs_rev.reverse()
        return [self._combine_pack(pack) for pack in packs_rev]

    def _choose_pack(self, forward: list[Chunk], backward: list[Chunk]) -> list[Chunk]:
        def score(packs: list[Chunk]) -> tuple[int, int]:
            return (len(packs), -min(len(p.content) for p in packs))

        if score(backward) < score(forward):
            return backward
        return forward

    def _combine_pack(self, pack: list[Chunk]) -> Chunk:
        first = pack[0]
        if len(pack) == 1:
            return first
        return Chunk(
            num_id=first.num_id,
            filename=first.filename,
            section_name=first.section_name,
            section_num_id=first.section_num_id,
            valid=first.valid,
            content=self._PACK_SEP.join(chunk.content for chunk in pack),
        )

    @classmethod
    def count_size_flags(
        cls, chunks: list[Chunk], pack_limit_chars: int | None
    ) -> tuple[int, int]:
        """Count final chunks below the minimum size or above the pack budget."""
        small = sum(1 for chunk in chunks if len(chunk.content) < cls.WARN_MIN_CHARS)
        if pack_limit_chars is None or pack_limit_chars <= 0:
            return small, 0
        oversize = sum(1 for chunk in chunks if len(chunk.content) > pack_limit_chars)
        return small, oversize

    def _log_final_file_chunks(
        self,
        chunks: list[Chunk],
        filename: str,
        section_name: str,
        limit: int | None,
    ) -> None:
        if not chunks:
            logger.debug(f"{section_name}:{filename}: 0 final chunks")
            return
        sizes = [len(chunk.content) for chunk in chunks]
        small, oversize = self.count_size_flags(chunks, limit)
        logger.debug(
            f"{section_name}:{filename}: {len(chunks)} final chunk(s), "
            f"min {min(sizes)} chars, max {max(sizes)} chars, "
            f"{small} below {self.WARN_MIN_CHARS}, {oversize} over budget"
        )
        if small:
            logger.info(
                f"{small} chunk(s) shorter than {self.WARN_MIN_CHARS} characters "
                f"in {filename} (section '{section_name}'). Split may be too fine."
            )
        if oversize and limit is not None:
            logger.info(
                f"{oversize} chunk(s) exceed pack_limit_chars ({limit}) "
                f"in {filename} (section '{section_name}'). "
                f"Overflow patterns did not reduce them."
            )

    @staticmethod
    def _is_content_valid(content: str, exclude_patterns: list[str], include_patterns: list[str]) -> bool:
        """
        Refines the list of chunks using a strict 'Exclude First' logic.
        """

        # 1. Check for Exclude Veto (Case-insensitive)
        if any(re.search(p, content, re.M | re.I) for p in exclude_patterns):
            return False
        # 2. Check for Include Permission
        # If no include_filters are defined, everything that wasn't excluded passes.
        if include_patterns:
            if not any(re.search(p, content, re.M | re.I) for p in include_patterns):
                return False

        # got it
        return True

    @staticmethod
    def _max_chunks(ep: ExecutionParameters) -> int:
        setting = ep.max_chunks_int_setting
        if setting.is_set and isinstance(setting.value, int) and setting.value >= 1:
            return setting.value
        return MaterialTokenizer.DEFAULT_MAX_CHUNKS


class MaterialTokenizerError(Exception):
    pass
