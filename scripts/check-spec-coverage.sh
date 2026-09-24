#!/usr/bin/env bash
# Consistency and coverage check for design/specs/.
#
#  1. Every code in the register (design/README.md, "Register of codes") is
#     exactly four upper-case letters, has the type functional or technical, and
#     points to an existing specification.
#  2. Every specification file is registered, and its file name and its header
#     fields "Code" and "Type" agree with the register.
#  3. Every acceptance criterion carries the code of its own specification and
#     is defined only once.
#  4. Every criterion is referenced by at least one test, and every identifier
#     with a registered code referenced in tests/ exists.
#
# Criteria marked *withdrawn* or *proposed* on their defining line are exempt from 4:
# withdrawn ones no longer apply, proposed ones are not implemented yet.
#
# Portable: runs with Bash 3.2 and the BSD tools of macOS as well as with GNU tools.
# All findings are reported before exiting; exit status 1 if there are any.
set -euo pipefail
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo "$(dirname "$0")/..")"

readonly REGISTER=design/README.md
readonly SPECS=design/specs
findings=0
report() { echo "  $*"; findings=$((findings + 1)); }
trim() { tr -d '[:space:]'; }

# --- 1. Register ------------------------------------------------------------
# Rows below the heading "Register of codes" of the form:
#   | `CODE` | <type> | `specs/<file>.md` ... |
# Result: one line per row, "CODE TYPE design/specs/<file>.md".
register=$(awk '
    /^## Register of codes/ { in_reg = 1; next }
    /^## / { in_reg = 0 }
    in_reg && /^\| `[^`]*` \|[^|]*\| `[^`]*`/ {
        split($0, col, "|"); type = col[3]; gsub(/^ +| +$/, "", type)
        split($0, cell, "`")
        print cell[2], (type == "" ? "-" : type), "design/" cell[4]
    }' "${REGISTER}")

echo "Register (${REGISTER}):"
[[ -z "${register}" ]] && report "no codes registered"
while read -r code type file; do
    [[ -z "${code}" ]] && continue
    [[ "${code}" =~ ^[A-Z]{4}$ ]] || report "code '${code}' is not exactly four upper-case letters"
    [[ "${type}" == functional || "${type}" == technical ]] \
        || report "code ${code} has type '${type}', expected functional or technical"
    [[ -f "${file}" ]] || report "code ${code} points to missing file ${file}"
done <<< "${register}"
dupes=$(awk '{ print $1 }' <<< "${register}" | sort | uniq -d)
[[ -n "${dupes}" ]] && while read -r d; do report "code ${d} registered twice"; done <<< "${dupes}"

# --- 2. and 3. Specifications -----------------------------------------------
defined=""
for spec in "${SPECS}"/*.md; do
    [[ -e "${spec}" ]] || continue
    echo "${spec}:"
    row=$(awk -v f="${spec}" '$3 == f { print $1, $2; exit }' <<< "${register}")
    if [[ -z "${row}" ]]; then
        report "not registered in ${REGISTER}"
        continue
    fi
    code=${row%% *}
    type=${row#* }
    lower=$(tr '[:upper:]' '[:lower:]' <<< "${code}")
    name=$(basename "${spec}")
    [[ "${name}" == "spec-${lower}-"*.md ]] || report "file name should start with spec-${lower}-"

    header=$(grep -oE '^\| Code \| `[^`]*` \|' "${spec}" | cut -d'`' -f2 || true)
    [[ "${header}" == "${code}" ]] || report "header field Code is '${header:-missing}', register says ${code}"
    htype=$(grep -oE '^\| Type \| [a-z]+ \|' "${spec}" | cut -d'|' -f3 | trim || true)
    [[ "${htype}" == "${type}" ]] || report "header field Type is '${htype:-missing}', register says ${type}"

    # Any line that looks like a criterion definition, whatever its prefix.
    ids=$(grep -oE '^- \*\*[A-Za-z]+-[0-9]+\*\*' "${spec}" | sed -E 's/^- \*\*//; s/\*\*$//' || true)
    if [[ -n "${ids}" ]]; then
        while read -r crit; do
            [[ "${crit}" =~ ^${code}-[0-9]{2,}$ ]] || report "criterion ${crit} does not match ${code}-NN"
        done <<< "${ids}"
        dupes=$(sort <<< "${ids}" | uniq -d)
        [[ -n "${dupes}" ]] && while read -r d; do report "criterion ${d} defined more than once"; done <<< "${dupes}"
    fi

    defined="${defined}$(grep -E "^- \*\*${code}-[0-9]{2,}\*\*" "${spec}" \
        | grep -v -E '\*(withdrawn|proposed)\*' | grep -oE "${code}-[0-9]{2,}" || true)
"
done

# --- 4. Coverage by tests ---------------------------------------------------
echo "Coverage (tests/):"
codes=$(awk '{ print $1 }' <<< "${register}" | paste -sd'|' -)
defined=$(sed '/^$/d' <<< "${defined}" | sort -u)
referenced=""
[[ -n "${codes}" ]] && referenced=$(grep -rhowE "(${codes})-[0-9]+" tests/ --include='*.py' | sort -u || true)

while read -r id; do [[ -n "${id}" ]] && report "${id} has no test"; done \
    < <(comm -23 <(echo "${defined}") <(echo "${referenced}"))
while read -r id; do [[ -n "${id}" ]] && report "${id} is referenced in tests but not defined (or withdrawn/proposed)"; done \
    < <(comm -13 <(echo "${defined}") <(echo "${referenced}"))

echo
if (( findings )); then
    echo "${findings} finding(s)."
    exit 1
fi
count=$(sed '/^$/d' <<< "${defined}" | wc -l | trim)
echo "OK: ${count} criteria, all registered, all referenced by tests."
