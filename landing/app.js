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

function init() {
  setText("year", String(new Date().getFullYear()));
  loadLatestRelease();
}

document.addEventListener("DOMContentLoaded", init);

