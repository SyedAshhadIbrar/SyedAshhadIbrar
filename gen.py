"""Builds the neofetch-style profile cards (dark_mode.svg, light_mode.svg).

Runs daily in .github/workflows/profile.yml. Without GITHUB_TOKEN the stats block is skipped (local preview).
"""
import datetime
import json
import os
import time
import urllib.request
from xml.sax.saxutils import escape

USER = 'SyedAshhadIbrar'
JOINED = datetime.date(2024, 7, 18)  # GitHub account creation date
WIDTH = 56  # info column width in characters
CHAR_W, LINE_H, PAD = 8.4, 20, 24  # 14px monospace metrics; ascii.txt is generated for this 0.42 aspect

THEMES = {
    'dark': dict(bg='#0d1117', border='#30363d', fg='#c9d1d9', key='#ffa657', val='#a5d6ff', dot='#484f58', add='#3fb950', dele='#f85149'),
    'light': dict(bg='#f6f8fa', border='#d0d7de', fg='#24292f', key='#953800', val='#0a3069', dot='#afb8c1', add='#1a7f37', dele='#cf222e'),
}


def plural(n, word):
    return f'{n} {word}' + ('s' if n != 1 else '')


def uptime(start, today):
    y, m, d = today.year - start.year, today.month - start.month, today.day - start.day
    if d < 0:
        m -= 1
        d += (today.replace(day=1) - datetime.timedelta(days=1)).day  # days in the previous month
    if m < 0:
        y, m = y - 1, m + 12
    return f'{plural(y, "year")}, {plural(m, "month")}, {plural(d, "day")}'


def github_stats():
    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        return None
    # shortcut: stars summed over the first 100 repos only, paginate if that is ever exceeded
    query = '''query($u: String!) { user(login: $u) {
      followers { totalCount }
      repositories(ownerAffiliations: OWNER, privacy: PUBLIC, first: 100) { totalCount nodes { name stargazerCount } }
      contributionsCollection { contributionCalendar { totalContributions } } } }'''
    req = urllib.request.Request(
        'https://api.github.com/graphql',
        json.dumps({'query': query, 'variables': {'u': USER}}).encode(),
        {'Authorization': f'bearer {token}'},
    )
    user = json.load(urllib.request.urlopen(req))['data']['user']
    repos = user['repositories']
    pairs = [
        ('Repos', repos['totalCount']),
        ('Stars', sum(n['stargazerCount'] for n in repos['nodes'])),
        ('Followers', user['followers']['totalCount']),
        ('Contributions (1y)', user['contributionsCollection']['contributionCalendar']['totalContributions']),
    ]
    return pairs, lines_of_code(token, [n['name'] for n in repos['nodes']])


def lines_of_code(token, repo_names):
    """Lines added and deleted by USER across their repos, from GitHub's per-contributor weekly stats."""
    added = deleted = 0
    for name in repo_names:
        req = urllib.request.Request(f'https://api.github.com/repos/{USER}/{name}/stats/contributors',
                                     headers={'Authorization': f'bearer {token}'})
        data = None
        for _ in range(10):  # GitHub answers 202 while it computes the stats
            resp = urllib.request.urlopen(req)
            if resp.status != 202:
                data = json.loads(resp.read() or b'[]')  # 204 = empty repo
                break
            time.sleep(3)
        # shortcut: a repo whose stats never finish computing is skipped; the next daily run includes it
        for contributor in data or []:
            if (contributor.get('author') or {}).get('login') == USER:
                added += sum(w['a'] for w in contributor['weeks'])
                deleted += sum(w['d'] for w in contributor['weeks'])
    return added, deleted


def info_lines(stats):
    """Each line is a list of (css_class, text) spans."""
    def kv(key, value):
        value = str(value)
        dots = WIDTH - len(key) - len(value) - 3
        assert dots >= 2, f'{key} value too long'
        return [('k', key), ('', ':'), ('d', ' ' + '.' * dots + ' '), ('v', value)]

    def section(title):
        return [('d', '- '), ('k', title), ('d', ' ' + '-' * (WIDTH - len(title) - 3))]

    def loc(added, deleted):
        key, net, tail = 'Lines of Code', f'{added - deleted:,}', [('', ' ( '), ('add', f'{added:,}++'), ('', ', '), ('dele', f'{deleted:,}--'), ('', ' )')]
        dots = WIDTH - len(key) - len(net) - sum(len(t) for _, t in tail) - 3
        return [('k', key), ('', ':'), ('d', ' ' + '.' * max(dots, 2) + ' '), ('v', net)] + tail

    lines = [
        [('k', 'syed'), ('', '@'), ('k', 'ashhad')],
        [('d', '-' * WIDTH)],
        kv('OS', 'Windows 11'),
        kv('Uptime', uptime(JOINED, datetime.date.today())),
        kv('Host', 'AI/ML & LLM Engineer'),
        kv('Kernel', 'ML · LLMs · RAG · Agents · Evals'),
        kv('Domain', 'Healthcare AI'),
        kv('IDE', 'Cursor, Jupyter'),
        [],
        kv('Languages.Programming', 'Python, MATLAB, JavaScript'),
        kv('Languages.Real', 'English, Urdu'),
        kv('Stack.ML', 'scikit-learn, XGBoost, LightGBM, CatBoost'),
        kv('Stack.LLM', 'LangChain, LlamaIndex, Hugging Face'),
        kv('Stack.Evals', 'RAGAS, DeepEval, LangSmith, Langfuse'),
        kv('Stack.Serving', 'FastAPI, Docker, AWS, GCP'),
        kv('Focus', 'ML models, LLM agents, grounded RAG'),
        kv('Hobbies.Software', 'Reading papers, side projects'),
        [],
        section('Contact'),
        kv('LinkedIn', 'syed-ashhad-ibrar'),
        kv('Email', 'syedashhadibrar8@gmail.com'),
    ]
    if stats:
        pairs, (added, deleted) = stats
        lines += [[], section('GitHub Stats')] + [kv(k, v) for k, v in pairs] + [loc(added, deleted)]
    return lines


def render(theme, art, info):
    c = THEMES[theme]
    info_x = PAD + (max(map(len, art)) + 3) * CHAR_W
    art_h, info_h = len(art) * LINE_H, len(info) * LINE_H
    w, h = info_x + WIDTH * CHAR_W + PAD, max(art_h, info_h) + 2 * PAD
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" xml:space="preserve" width="{w:.0f}" height="{h}" viewBox="0 0 {w:.0f} {h}">',
        f'<style>text{{white-space:pre;font:14px Consolas,"DejaVu Sans Mono","Courier New",monospace;fill:{c["fg"]}}}'
        f'.k{{fill:{c["key"]}}}.v{{fill:{c["val"]}}}.d{{fill:{c["dot"]}}}.add{{fill:{c["add"]}}}.dele{{fill:{c["dele"]}}}</style>',
        f'<rect width="100%" height="100%" rx="12" fill="{c["bg"]}" stroke="{c["border"]}"/>',
    ]
    art_top, info_top = PAD + (h - 2 * PAD - art_h) / 2, PAD + (h - 2 * PAD - info_h) / 2  # center both columns
    for i, line in enumerate(art):
        out.append(f'<text x="{PAD}" y="{art_top + (i + 1) * LINE_H - 5:.0f}">{escape(line)}</text>')
    for i, spans in enumerate(info):
        if spans:
            body = ''.join(f'<tspan class="{cls}">{escape(t)}</tspan>' if cls else escape(t) for cls, t in spans)
            out.append(f'<text x="{info_x:.1f}" y="{info_top + (i + 1) * LINE_H - 5:.0f}">{body}</text>')
    out.append('</svg>')
    return '\n'.join(out)


assert uptime(datetime.date(2024, 7, 18), datetime.date(2026, 10, 22)) == '2 years, 3 months, 4 days'
assert uptime(datetime.date(2024, 7, 18), datetime.date(2026, 3, 10)) == '1 year, 7 months, 20 days'

if __name__ == '__main__':
    here = os.path.dirname(os.path.abspath(__file__))
    info = info_lines(github_stats())
    with open(os.path.join(here, 'ascii.txt'), encoding='utf-8') as f:
        art = f.read().splitlines()
    for theme in THEMES:
        with open(os.path.join(here, f'{theme}_mode.svg'), 'w', encoding='utf-8') as f:
            f.write(render(theme, art, info))
