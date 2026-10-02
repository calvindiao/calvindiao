import { writeFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { dirname, join } from 'node:path';
import { pathToFileURL } from 'node:url';

// Use the maintained Readme Stats renderer with narrowly scoped public queries.
// Its general-purpose fetcher requests fields unavailable to GITHUB_TOKEN.
const require = createRequire(import.meta.url);
const core = dirname(require.resolve('@stats-organization/github-readme-stats-core'));
const { renderStatsCard } = await import(pathToFileURL(join(core, 'cards/stats.js')));

const username = process.env.GITHUB_USERNAME || 'calvindiao';
const token = process.env.GITHUB_TOKEN;
if (!token) throw new Error('GITHUB_TOKEN is required to collect public activity.');
if (!/^[A-Za-z0-9-]+$/.test(username)) throw new Error('Invalid GitHub username.');

async function api(path, body) {
  const response = await fetch(`https://api.github.com/${path}`, {
    method: body ? 'POST' : 'GET',
    headers: {
      Accept: 'application/vnd.github+json',
      Authorization: `Bearer ${token}`,
      'X-GitHub-Api-Version': '2022-11-28',
      'Content-Type': 'application/json',
    },
    body: body ? JSON.stringify(body) : undefined,
    signal: AbortSignal.timeout(30_000),
  });
  if (!response.ok) throw new Error(`GitHub public activity request failed (${response.status}).`);
  const data = await response.json();
  if (data.errors?.length) throw new Error(`GitHub GraphQL: ${data.errors.map(e => e.message).join('; ')}`);
  if (data.incomplete_results) throw new Error('GitHub search returned incomplete activity counts.');
  return data;
}

async function repositories() {
  const all = [];
  for (let page = 1; ; page++) {
    const batch = await api(`users/${username}/repos?type=owner&per_page=100&page=${page}`);
    all.push(...batch.filter(repo => !repo.private));
    if (batch.length < 100) return all;
  }
}

const now = new Date();
const year = now.getUTCFullYear();
const from = `${year}-01-01T00:00:00Z`;
const query = `query($login:String!,$from:DateTime!,$to:DateTime!) {
  user(login:$login) {
    contributionsCollection(from:$from,to:$to) {
      commitContributionsByRepository(maxRepositories:100) {
        repository { isPrivate }
        contributions { totalCount }
      }
    }
  }
}`;

const [repos, prs, issues, contributions] = await Promise.all([
  repositories(),
  api(`search/issues?q=${encodeURIComponent(`author:${username} type:pr is:public`)}&per_page=1`),
  api(`search/issues?q=${encodeURIComponent(`author:${username} type:issue is:public`)}&per_page=1`),
  api('graphql', { query, variables: { login: username, from, to: now.toISOString() } }),
]);

const byRepo = contributions.data?.user?.contributionsCollection?.commitContributionsByRepository;
if (!byRepo || byRepo.length === 100) throw new Error('Could not obtain a complete public commit count.');
const counts = {
  totalStars: repos.reduce((sum, repo) => sum + repo.stargazers_count, 0),
  totalPRs: prs.total_count,
  totalIssues: issues.total_count,
  totalCommits: byRepo.filter(item => !item.repository.isPrivate).reduce((sum, item) => sum + item.contributions.totalCount, 0),
};
for (const [name, count] of Object.entries(counts)) {
  if (!Number.isSafeInteger(count) || count < 0) throw new Error(`Invalid activity count: ${name}.`);
}

const themes = {
  latte: { title_color: '8839ef', text_color: '4c4f69', icon_color: '7287fd', bg_color: 'eff1f5', border_color: 'ccd0da' },
  mocha: { title_color: 'cba6f7', text_color: 'cdd6f4', icon_color: '89b4fa', bg_color: '1e1e2e', border_color: '313244' },
};

for (const [theme, colors] of Object.entries(themes)) {
  let svg = renderStatsCard({
    name: 'Calvin Diao', ...counts,
    // The rank is disabled; its required rendering value is never displayed.
    rank: { level: '', percentile: 100 },
  }, {
    ...colors, custom_title: 'GitHub activity', commits_year: year,
    hide: ['contribs'], hide_rank: true, show_icons: true, hide_border: false,
    disable_animations: true, card_width: 350, line_height: 32,
    border_radius: 12, text_bold: false,
  }, username);
  if (!svg.includes('<svg') || /Something went wrong|Resource not accessible/i.test(svg)) {
    throw new Error('Stats renderer returned an error card.');
  }
  // Only enlarge the stat text. The existing label and value columns still have
  // room for the longest English label at 16px; retain all their coordinates.
  const statFont = /(\.stat\s*\{\s*font:\s*600\s+)14px\b/g;
  if ([...svg.matchAll(statFont)].length !== 1) throw new Error('Stats font styling changed upstream.');
  svg = svg.replace(statFont, (_, prefix) => `${prefix}16px`)
    .replace('.stat { font-size:12px; }', '.stat { font-size:16px; }');
  await writeFile(new URL(`../profile/stats-${theme}.svg`, import.meta.url), svg);
}
console.log(`Rendered public GitHub activity for ${year}: ${JSON.stringify(counts)}`);
