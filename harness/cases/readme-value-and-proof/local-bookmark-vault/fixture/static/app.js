// Local Bookmark Vault — vanilla JS frontend, no build step, no dependencies.

const list = document.getElementById("bookmarks");
const tagFilter = document.getElementById("tag-filter");
const addForm = document.getElementById("add-form");

async function fetchBookmarks(tag) {
  const url = tag ? `/api/bookmarks?tag=${encodeURIComponent(tag)}` : "/api/bookmarks";
  const res = await fetch(url);
  return res.json();
}

function render(bookmarks) {
  list.innerHTML = "";
  for (const b of bookmarks) {
    const li = document.createElement("li");
    const a = document.createElement("a");
    a.href = b.url;
    a.textContent = b.title;
    a.target = "_blank";
    li.appendChild(a);
    if (b.tag) {
      const tag = document.createElement("span");
      tag.className = "tag";
      tag.textContent = ` [${b.tag}]`;
      li.appendChild(tag);
    }
    const del = document.createElement("button");
    del.textContent = "delete";
    del.onclick = async () => {
      await fetch(`/api/bookmarks/${b.id}`, { method: "DELETE" });
      refresh();
    };
    li.appendChild(del);
    list.appendChild(li);
  }
}

function refreshTagOptions(bookmarks) {
  const tags = [...new Set(bookmarks.map((b) => b.tag).filter(Boolean))];
  const current = tagFilter.value;
  tagFilter.innerHTML = '<option value="">(all)</option>';
  for (const t of tags) {
    const opt = document.createElement("option");
    opt.value = t;
    opt.textContent = t;
    tagFilter.appendChild(opt);
  }
  tagFilter.value = current;
}

async function refresh() {
  const all = await fetchBookmarks(null);
  refreshTagOptions(all);
  const filtered = tagFilter.value ? await fetchBookmarks(tagFilter.value) : all;
  render(filtered);
}

addForm.addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const url = document.getElementById("url").value;
  const title = document.getElementById("title").value;
  const tag = document.getElementById("tag").value;
  await fetch("/api/bookmarks", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, title, tag }),
  });
  addForm.reset();
  refresh();
});

tagFilter.addEventListener("change", refresh);

refresh();
