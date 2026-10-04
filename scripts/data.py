"""Data for the profile: Chromium changes (public Gerrit) and the contribution count (GitHub).

Offline is the default: everything is read from the committed snapshots in data/. With live=True the
snapshots are refreshed first, and *every* failure path (network down, Gerrit changes its format,
an implausible answer, a damaged snapshot) keeps the last good data, prints a warning and carries on,
so a bad day can never produce an empty, broken or error-card image.

data/gerrit.json   {"as_of": "YYYY-MM-DD", "changes": [{_number, status, subject, created, submitted,
                   insertions, deletions}, ...]}   only MERGED and NEW (in review) changes; a NEW
                   change still marked work-in-progress is not in review yet and is left out
data/github.json   {"contributions_last_year": N, "as_of": "YYYY-MM-DD"}

A snapshot that is missing or malformed is treated as "nothing known yet": the page then draws what it
can (no changes, no score, no save date) instead of crashing, and never prints a zero or a made-up value.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from pixelkit import clean, read_text, write_text

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
GERRIT_OWNER = 'diaochenhao@gmail.com'
GERRIT_URL = 'https://chromium-review.googlesource.com'
GERRIT_PROJECT = 'chromium/src'
SHOWN = ('MERGED', 'NEW')  # abandoned changes are never shown
DATE = re.compile(r'^\d{4}-\d{2}-\d{2}')


def warn(msg: str) -> None:
    """A GitHub Actions annotation when running in CI, a plain line otherwise."""
    if os.environ.get('GITHUB_ACTIONS') == 'true':
        print(f'::warning title=Profile data::{msg}')
    else:
        print(f'warning: {msg}', file=sys.stderr)


def _read(name: str):
    """The parsed snapshot, or None when it is missing, unreadable or not JSON."""
    try:
        return json.loads(read_text(DATA / name))
    except (OSError, ValueError):  # ValueError covers a JSON error and bad UTF-8
        return None


def _write(name: str, obj) -> None:
    text = json.dumps(obj, indent=1, ensure_ascii=False) + '\n'
    path = DATA / name
    try:
        same = read_text(path) == text
    except (OSError, ValueError):
        same = False
    if not same:
        DATA.mkdir(exist_ok=True)
        write_text(path, text)


def _date(v):
    """'YYYY-MM-DD' for a real calendar date (any trailing time is dropped), else None."""
    if isinstance(v, str) and DATE.match(v):
        try:
            datetime.strptime(v[:10], '%Y-%m-%d')
        except ValueError:
            return None
        return v[:10]
    return None


def _count(v):
    """A non-negative integer, else None (a bool is not a count)."""
    return v if isinstance(v, int) and not isinstance(v, bool) and v >= 0 else None


def _is_wip(c):
    """A NEW change Gerrit still marks work-in-progress (uploaded, but not sent for review)."""
    return isinstance(c, dict) and c.get('status') == 'NEW' and c.get('work_in_progress') is True


def change_row(c):
    """One Gerrit change reduced to the fields worth keeping, or None when it is unusable.

    A change without a number, a shown status, a subject or a real creation date cannot be drawn and is
    dropped. So is a work-in-progress upload: Gerrit reports it as NEW, but nobody is reviewing it yet, so
    it must not be drawn as "in review". Line counts are optional: when Gerrit gave none they stay absent
    (the card then says so instead of printing +0 -0).
    """
    if not isinstance(c, dict) or c.get('status') not in SHOWN or _is_wip(c):
        return None
    num = c.get('_number')
    subject = clean(c.get('subject') or '')
    created = _date(c.get('created'))
    if not (isinstance(num, int) and not isinstance(num, bool) and num > 0 and subject and created):
        return None
    row = {'_number': num, 'status': c['status'], 'subject': subject, 'created': c['created']}
    sub = c.get('submitted')
    if c['status'] == 'MERGED' and _date(sub):
        row['submitted'] = sub
    for k in ('insertions', 'deletions'):
        n = _count(c.get(k))
        if n is not None:
            row[k] = n
    return row


def _sorted(rows):
    return sorted(rows, key=lambda r: (r['created'], r['_number']))


def _get(url, headers, data=None, timeout=25, tries=2):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode('utf-8')
        except Exception as e:  # noqa: BLE001 - retried once, then reported by the caller
            last = e
            if i + 1 < tries:
                time.sleep(3)
    raise last


def fetch_gerrit():
    q = urllib.parse.quote(f'owner:{GERRIT_OWNER}', safe=':@')
    body = _get(f'{GERRIT_URL}/changes/?q={q}&n=100', {'User-Agent': 'calvindiao-profile'}).lstrip()
    if body.startswith(")]}'"):  # Gerrit's XSSI guard, always the first line
        body = body.split('\n', 1)[1] if '\n' in body else ''
    rows = json.loads(body)
    if not isinstance(rows, list):
        raise ValueError('Gerrit did not answer with a list')
    out, dropped = [], 0
    for c in rows:
        if isinstance(c, dict) and c.get('project') != GERRIT_PROJECT:
            continue
        row = change_row(c)
        if row:
            out.append(row)
        elif isinstance(c, dict) and c.get('status') in SHOWN and not _is_wip(c):
            dropped += 1  # a work-in-progress change is skipped on purpose, not a problem worth a warning
    if dropped:
        warn(f'{dropped} Gerrit change(s) were unusable and skipped')
    return _sorted(out)


def fetch_contributions():
    token = os.environ.get('GITHUB_TOKEN')
    user = os.environ.get('GITHUB_USERNAME', 'calvindiao')
    if not token:
        raise RuntimeError('no GITHUB_TOKEN')
    q = 'query($l:String!){user(login:$l){contributionsCollection{contributionCalendar{totalContributions}}}}'
    body = _get('https://api.github.com/graphql',
                {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json', 'User-Agent': 'calvindiao-profile'},
                data=json.dumps({'query': q, 'variables': {'l': user}}).encode())
    n = json.loads(body)['data']['user']['contributionsCollection']['contributionCalendar']['totalContributions']
    if not isinstance(n, int) or isinstance(n, bool) or n <= 0:
        raise ValueError(f'implausible contribution count {n!r}')  # the page never shows a zero
    return n


def _snapshot_changes(live):
    snap = _read('gerrit.json')
    if not isinstance(snap, dict) or not isinstance(snap.get('changes'), list):
        warn('data/gerrit.json is missing or damaged; ' + ('asking Gerrit instead' if live else 'no Chromium changes known'))
        return [], None
    return _sorted(r for r in map(change_row, snap['changes']) if r), _date(snap.get('as_of'))


def _snapshot_score(live):
    snap = _read('github.json')
    if not isinstance(snap, dict):
        warn('data/github.json is missing or damaged; ' + ('asking GitHub instead' if live else 'no contribution count known'))
        return None, None
    n = snap.get('contributions_last_year')
    return (n if _count(n) else None), _date(snap.get('as_of'))  # a zero is never shown


def load(live: bool = False) -> dict:
    """{'cls': [change, ...], 'score': int | None, 'last_save': 'YYYY-MM-DD' | None}.

    last_save is the date the *older* of the two sources was refreshed, so a source that has been
    failing shows in the footer instead of being hidden by the other one succeeding.

    The one case that cannot be survived is a live run with no Chromium data at all (damaged snapshot
    and Gerrit unreachable): it exits non-zero, so CI keeps the committed profile instead of
    overwriting it with an empty page.
    """
    changes, gerrit_as_of = _snapshot_changes(live)
    score, score_as_of = _snapshot_score(live)
    if live:
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        try:
            fresh = fetch_gerrit()
            merged_old = sum(c['status'] == 'MERGED' for c in changes)
            merged_new = sum(c['status'] == 'MERGED' for c in fresh)
            if merged_new < merged_old:  # a merged change never un-merges: fail closed
                raise ValueError(f'implausible answer: {merged_new} merged, {merged_old} already known')
            if not fresh:
                raise ValueError('no changes in the answer')
        except Exception as e:  # noqa: BLE001
            warn(f'Gerrit refresh failed ({e})' + (f', keeping the snapshot from {gerrit_as_of}' if changes else ''))
        else:
            changes, gerrit_as_of = fresh, today  # fresh data is used even if saving it fails below
            try:
                _write('gerrit.json', {'as_of': today, 'changes': changes})
            except OSError as e:
                warn(f'could not save data/gerrit.json ({e})')
        try:
            fresh_score = fetch_contributions()
        except Exception as e:  # noqa: BLE001
            warn(f'contribution count refresh failed ({e})' + (f', keeping the snapshot from {score_as_of}' if score else ''))
        else:
            score, score_as_of = fresh_score, today
            try:
                _write('github.json', {'contributions_last_year': score, 'as_of': today})
            except OSError as e:
                warn(f'could not save data/github.json ({e})')
    if live and not changes:
        raise SystemExit('no Chromium changes: data/gerrit.json is unusable and Gerrit gave nothing, '
                         'so the committed profile is left as it is')
    cls = []
    for i, c in enumerate(changes):
        c = dict(c)
        c['stage'] = f'1-{i + 1}'
        c['url'] = f'{GERRIT_URL}/c/chromium/src/+/{c["_number"]}'
        c['when'] = (c.get('submitted') or c['created'])[:10]
        cls.append(c)
    dates = [d for d in (gerrit_as_of, score_as_of) if d]
    return {'cls': cls, 'score': score, 'last_save': min(dates) if dates else None}
