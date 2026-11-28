#!/bin/sh
# GitHub Flow squashes every PR into a single commit on main, so the PR title
# becomes the permanent commit subject. This checks it before merge, while the
# author can still fix it in the browser.
#
# Input: $PR_TITLE (set by the workflow from the pull request event),
#        or the first argument when running it by hand:
#           sh scripts/check-pr-title.sh "fix(queue): do not re-claim a locked row"

set -u

title=${PR_TITLE:-${1:-}}

if [ -z "$title" ]; then
  echo "check-pr-title: no title given (set PR_TITLE or pass it as an argument)" >&2
  exit 1
fi

length=$(printf '%s' "$title" | wc -c | tr -d ' ')
if [ "$length" -gt 72 ]; then
  echo "check-pr-title: title is $length characters, limit is 72 - it is a commit subject, not a paragraph" >&2
  exit 1
fi

case "$title" in
  feat*|fix*|docs*|test*|refactor*|perf*|chore*|ci*|build*|revert*) ;;
  *)
    echo "check-pr-title: expected 'type(scope): subject', got: $title" >&2
    echo "  allowed types: feat fix docs test refactor perf chore ci build revert" >&2
    exit 1
    ;;
esac

# 'type(scope): subject' - scope is optional, subject must start lowercase and
# must not end in a full stop.
case "$title" in
  *": "*)
    prefix=${title%%: *}
    subject=${title#*: }
    ;;
  *)
    echo "check-pr-title: missing ': ' between type and subject, got: $title" >&2
    exit 1
    ;;
esac

case "$prefix" in
  *'()'*)
    echo "check-pr-title: empty scope - drop the parentheses or name the module" >&2
    exit 1
    ;;
  *'('*')') ;;
  *'('*|*')'*)
    echo "check-pr-title: unbalanced scope parentheses in: $prefix" >&2
    exit 1
    ;;
  # a bare type is fine: 'docs: correct the retry table'
  feat|fix|docs|test|refactor|perf|chore|ci|build|revert) ;;
  *)
    echo "check-pr-title: '$prefix' is not a bare type - use type(scope): subject" >&2
    exit 1
    ;;
esac

case "$subject" in
  "") echo "check-pr-title: empty subject after ': ' " >&2; exit 1 ;;
  [A-Z]*) echo "check-pr-title: subject starts with a capital - commit subjects are lowercase" >&2; exit 1 ;;
  *.) echo "check-pr-title: subject ends with a full stop" >&2; exit 1 ;;
esac

echo "check-pr-title: ok - $title"
