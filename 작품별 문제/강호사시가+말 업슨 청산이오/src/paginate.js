// 2단 시험지 자동 쪽 나눔: #src의 .u 단위를 차례로 단에 채운다.
(function () {
  const src = document.getElementById('src');
  const units = [...src.children];
  const pages = [];
  let col = null, colIdx = 2;

  function header(n) {
    if (n === 1) return `<div class="top1">${HEAD} ${SUB}<span class="pn">1</span></div>
<div class="row1"><span class="kyo">제 1 교시</span><span class="subt">국어 영역</span><img class="logo" src="${LOGO}"></div><div class="rule"></div>`;
    return `<div class="topn"><span class="pn">${n}</span><span class="ra">RICH ACADEMY</span><span class="lg"><img src="${LOGO}"></span></div><div class="rule"></div>`;
  }
  function newPage() {
    const n = pages.length + 1;
    const p = document.createElement('div');
    p.className = 'page ' + (n % 2 ? 'odd' : 'even');
    p.innerHTML = header(n) + `<div class="cols" style="--top:${n === 1 ? '42mm' : '33mm'}"><div class="col"></div><div class="col"></div></div>
<div class="foot"><span class="fr"><i>${n}</i><s class="tot"></s></span></div>`;
    document.body.appendChild(p);
    pages.push(p);
    return p;
  }
  function nextCol() {
    if (colIdx >= 1 || !col) { newPage(); colIdx = 0; }
    else colIdx++;
    col = pages[pages.length - 1].querySelectorAll('.col')[colIdx];
  }
  const over = () => col.scrollHeight > col.clientHeight + 0.5;
  const empty = () => col.children.length === 0;

  // 지문: 줄 단위로 나눠서 단을 넘김
  function placeSet(u) {
    const hd = u.querySelector('.sethd');
    const lines = [...u.querySelector('.box').children];
    const make = (first) => {
      const w = document.createElement('div'); w.className = 'u set';
      if (first) w.appendChild(hd);
      const b = document.createElement('div'); b.className = 'box' + (first ? '' : ' cont');
      w.appendChild(b); col.appendChild(w); return [w, b];
    };
    let [w, b] = make(true);
    let i = 0;
    for (; i < Math.min(3, lines.length); i++) b.appendChild(lines[i]);
    if (over() && col.children.length > 1) { w.remove(); nextCol(); col.appendChild(w); }
    while (i < lines.length) {
      const l = lines[i];
      b.appendChild(l);
      if (over()) {
        b.removeChild(l);
        while (b.lastChild && b.lastChild.classList.contains('sp')) b.removeChild(b.lastChild);
        b.classList.add('open');
        nextCol();
        [w, b] = make(false);
        while (i < lines.length && lines[i].classList.contains('sp')) i++;
        continue;
      }
      i++;
    }
  }
  // 해설: 너무 길면 문단 단위로 나눔
  function placeSplittable(u) {
    col.appendChild(u);
    if (!over()) return;
    col.removeChild(u);
    if (!empty()) { nextCol(); col.appendChild(u); if (!over()) return; col.removeChild(u); }
    const kids = [...u.children];
    let w = u.cloneNode(false); col.appendChild(w);
    for (const k of kids) {
      w.appendChild(k);
      if (over()) { w.removeChild(k); nextCol(); w = u.cloneNode(false); w.classList.add('cont'); col.appendChild(w); w.appendChild(k); }
    }
  }
  function place(u) {
    if (u.classList.contains('brk')) { colIdx = 2; col = null; nextCol(); return; }
    if (u.classList.contains('set')) return placeSet(u);
    if (u.classList.contains('ex')) return placeSplittable(u);
    col.appendChild(u);
    if (over() && col.children.length > 1) { col.removeChild(u); nextCol(); col.appendChild(u); }
    if (u.classList.contains('extitle')) u.dataset.keep = 1;
  }
  // 시행이 한두 글자만 넘어가면 자간을 줄여 한 줄로
  document.querySelectorAll('#src .ln:not(.pr):not(.shp):not(.note):not(.sp)').forEach(l => {
    const lh = parseFloat(getComputedStyle(l).lineHeight);
    if (l.offsetHeight < lh * 1.5) return;
    for (const ls of ['-0.03em', '-0.06em', '-0.09em']) {
      l.style.letterSpacing = ls;
      if (l.offsetHeight < lh * 1.5) return;
    }
    l.style.letterSpacing = '';
  });
  nextCol();
  let pendingKeep = null;
  for (const u of units) {
    place(u);
  }
  src.remove();
  document.querySelectorAll('.tot').forEach(t => t.textContent = pages.length);
  // 단 끝의 여백 margin 제거
  document.querySelectorAll('.col').forEach(c => { const l = c.lastElementChild; if (l) l.style.marginBottom = '0'; });
  window.PAGES = pages.length;
  document.body.dataset.done = '1';
})();
