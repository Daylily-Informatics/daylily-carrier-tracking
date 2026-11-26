# Bash tab completion for `tday`.
#
# Usage (one-shot):
#   source <(tday completion bash)
#
# Usage (repo checkout):
#   source /path/to/daylily-carrier-tracking/completions/tday.bash
#
# Notes:
# - This registers completion for the command name `tday` only.

_tday_complete() {
  local cur prev
  cur="${COMP_WORDS[COMP_CWORD]}"
  prev=""
  if [ "$COMP_CWORD" -ge 1 ]; then
    prev="${COMP_WORDS[COMP_CWORD-1]}"
  fi

  local subcmds="test configure recognize track doctor completion"
  local global_opts="--pretty --no-color -h --help"

  # Value completion for flags that take an argument.
  case "$prev" in
    --carrier)
      COMPREPLY=( $(compgen -W "auto fedex ups usps" -- "$cur") )
      return 0
      ;;
    --api-preference)
      COMPREPLY=( $(compgen -W "track ship" -- "$cur") )
      return 0
      ;;
    --env)
      COMPREPLY=( $(compgen -W "prod test sandbox dev" -- "$cur") )
      return 0
      ;;
    --path|--config-path)
      COMPREPLY=( $(compgen -f -- "$cur") )
      return 0
      ;;
  esac

  # Find the first subcommand (global flags may appear before/after).
  local cmd=""
  local i
  for ((i=1; i<${#COMP_WORDS[@]}; i++)); do
    case "${COMP_WORDS[i]}" in
      test|configure|recognize|track|doctor|completion)
        cmd="${COMP_WORDS[i]}"
        break
        ;;
    esac
  done

  if [ -z "$cmd" ]; then
    if [[ "$cur" == -* ]]; then
      COMPREPLY=( $(compgen -W "$global_opts" -- "$cur") )
    else
      COMPREPLY=( $(compgen -W "$subcmds" -- "$cur") )
    fi
    return 0
  fi

  # `tday configure <carrier>` positional completion.
  if [ "$cmd" = "configure" ]; then
    local cmd_idx=-1
    for ((i=1; i<${#COMP_WORDS[@]}; i++)); do
      if [ "${COMP_WORDS[i]}" = "configure" ]; then
        cmd_idx=$i
        break
      fi
    done
    if [ "$cmd_idx" -ge 0 ] && [ "$COMP_CWORD" -eq $((cmd_idx + 1)) ]; then
      COMPREPLY=( $(compgen -W "fedex ups usps" -- "$cur") )
      return 0
    fi
  fi

  # `tday completion <shell>` positional completion.
  if [ "$cmd" = "completion" ]; then
    local cmd_idx=-1
    for ((i=1; i<${#COMP_WORDS[@]}; i++)); do
      if [ "${COMP_WORDS[i]}" = "completion" ]; then
        cmd_idx=$i
        break
      fi
    done
    if [ "$cmd_idx" -ge 0 ] && [ "$COMP_CWORD" -eq $((cmd_idx + 1)) ]; then
      COMPREPLY=( $(compgen -W "bash zsh" -- "$cur") )
      return 0
    fi
  fi

  local opts=""
  case "$cmd" in
    test)
      opts="$global_opts --test-fedex --test-ups --test-usps"
      ;;
    configure)
      opts="$global_opts --env --path --skip-validate"
      ;;
    track)
      opts="$global_opts --carrier --no-raw --api-preference"
      ;;
    doctor)
      opts="$global_opts --all --carrier --env --config-path --no-network --tracking-number --json"
      ;;
    completion|recognize)
      opts="$global_opts"
      ;;
  esac

  if [[ "$cur" == -* ]]; then
    COMPREPLY=( $(compgen -W "$opts" -- "$cur") )
  else
    COMPREPLY=()
  fi
  return 0
}

complete -F _tday_complete tday
