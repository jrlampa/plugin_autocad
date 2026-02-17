/* sisRUA landing — lightweight client script */

function setText(id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = text;
}

function setHref(id, href) {
  const el = document.getElementById(id);
  if (el && typeof href === "string" && href.length > 0) el.setAttribute("href", href);
}

async function loadLatestRelease() {
  const owner = "jrlampa";
  const repo = "plugin_autocad";
  const fallback = `https://github.com/${owner}/${repo}/releases/latest`;

  // Defaults (safe even if GitHub API rate limits)
  setHref("downloadTop", fallback);
  setHref("downloadHero", fallback);
  setHref("downloadCompare", fallback);
  setHref("downloadBottom", fallback);
  setText("latestVersion", "releases/latest");

  try {
    const resp = await fetch(`https://api.github.com/repos/${owner}/${repo}/releases/latest`, {
      headers: { Accept: "application/vnd.github+json" },
    });
    if (!resp.ok) throw new Error(`GitHub API: ${resp.status}`);
    const data = await resp.json();

    const tag = (data && (data.tag_name || data.name)) ? (data.tag_name || data.name) : null;
    if (tag) setText("latestVersion", tag);

    const assets = Array.isArray(data.assets) ? data.assets : [];
    const exe = assets.find((a) => {
      const n = (a && a.name) ? String(a.name) : "";
      return n.toLowerCase().endsWith(".exe") && n.toLowerCase().includes("sisrua") && n.toLowerCase().includes("installer");
    });

    const direct = exe && exe.browser_download_url ? exe.browser_download_url : fallback;
    setHref("downloadTop", direct);
    setHref("downloadHero", direct);
    setHref("downloadCompare", direct);
    setHref("downloadBottom", direct);
  } catch {
    // ignore: keep fallback
  }
}

async function loadRepoStats() {
  const owner = "jrlampa";
  const repo = "plugin_autocad";

  try {
    // Fetch repository info
    const repoResp = await fetch(`https://api.github.com/repos/${owner}/${repo}`, {
      headers: { Accept: "application/vnd.github+json" },
    });
    if (!repoResp.ok) throw new Error(`GitHub API: ${repoResp.status}`);
    const repoData = await repoResp.json();

    // Update stats
    if (repoData.stargazers_count !== undefined) {
      setText("repoStars", repoData.stargazers_count.toLocaleString("pt-BR"));
    }
    if (repoData.forks_count !== undefined) {
      setText("repoForks", repoData.forks_count.toLocaleString("pt-BR"));
    }
    if (repoData.subscribers_count !== undefined) {
      setText("repoWatchers", repoData.subscribers_count.toLocaleString("pt-BR"));
    }

    // Fetch releases count
    const releasesResp = await fetch(`https://api.github.com/repos/${owner}/${repo}/releases?per_page=100`, {
      headers: { Accept: "application/vnd.github+json" },
    });
    if (releasesResp.ok) {
      const releasesData = await releasesResp.json();
      if (Array.isArray(releasesData)) {
        setText("repoReleases", releasesData.length.toLocaleString("pt-BR"));
      }
    }
  } catch (error) {
    console.error('Failed to load GitHub stats:', error);
  }
}

async function loadGitHubStats() {
  const owner = "jrlampa";
  const repo = "plugin_autocad";

  try {
    // Fetch repository data
    const repoResp = await fetch(`https://api.github.com/repos/${owner}/${repo}`, {
      headers: { Accept: "application/vnd.github+json" },
    });
    if (!repoResp.ok) throw new Error(`GitHub API: ${repoResp.status}`);
    const repoData = await repoResp.json();

    // Update stats with locale formatting
    if (repoData.stargazers_count !== undefined) {
      setText("ghStars", repoData.stargazers_count.toLocaleString());
    }
    if (repoData.forks_count !== undefined) {
      setText("ghForks", repoData.forks_count.toLocaleString());
    }
    if (repoData.subscribers_count !== undefined) {
      setText("ghWatchers", repoData.subscribers_count.toLocaleString());
    }

    // Fetch releases count
    const releasesResp = await fetch(`https://api.github.com/repos/${owner}/${repo}/releases?per_page=100`, {
      headers: { Accept: "application/vnd.github+json" },
    });
    if (releasesResp.ok) {
      const releasesData = await releasesResp.json();
      if (Array.isArray(releasesData)) {
        setText("ghReleases", releasesData.length.toLocaleString());
      }
    }
  } catch (error) {
    // Keep "—" placeholders on error
    console.error('Failed to load GitHub stats:', error);
  }
}

function init() {
  setText("year", String(new Date().getFullYear()));
  loadLatestRelease();
  loadRepoStats();
  loadGitHubStats();
}

document.addEventListener("DOMContentLoaded", init);

