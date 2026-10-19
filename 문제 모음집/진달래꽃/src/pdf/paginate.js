// 2단 시험지 자동 쪽 나눔: #src의 .u 단위를 차례로 단에 채운다.
(function () {
  const src = document.getElementById('src');
  const units = [...src.children];
  const pages = [];
  let col = null, colIdx = 2;

  function header(n) {
    const box = '<span class="kt">이재규T</span>';
    if (n === 1) return `<div class="h1box"><div class="h1t">${HEAD}</div><span class="kyo">제1교시</span><img class="h1logo" src="${LOGO}">${box}<span class="pn1">1</span></div>`;
    return `<div class="topn"><span class="pn">${n}</span><span class="ra">RICH ACADEMY</span><span class="lg">${box}</span></div><div class="rule"></div>`;
  }
  function newPage() {
    const n = pages.length + 1;
    const p = document.createElement('div');
    p.className = 'page ' + (n % 2 ? 'odd' : 'even');
    p.innerHTML = header(n) + `<div class="cols" style="--top:${n === 1 ? '102mm' : '50mm'}"><div class="col"></div><div class="col"></div></div>
<div class="foot"><span class="fr"><i>${n}</i><s class="tot"></s></span></div>`;
    document.body.appendChild(p);
    pages.push(p);
    return p;
  }
  function nextCol() {
    if (colIdx >= 1 || !col) { newPage(); colIdx = 0; }
    else colIdx++;
    col = pages[pages.length - 1].querySelectorAll('.col')[colIdx];
    // 정답 및 해설 첫 쪽: 오른쪽 단 첫 해설을 왼쪽 단 첫 해설과 같은 높이에서 시작
    if (colIdx === 1) {
      const ext = pages[pages.length - 1].querySelector('.col .extitle');
      if (ext) {
        const cs = getComputedStyle(ext);
        const sp = document.createElement('div'); sp.className = 'u exsp';
        sp.style.height = (ext.offsetHeight + parseFloat(cs.marginTop) + parseFloat(cs.marginBottom)) + 'px';
        sp.style.margin = '0'; col.appendChild(sp);
      }
    }
  }
  const over = () => col.scrollHeight > col.clientHeight + 0.5;
  const empty = () => col.children.length === 0;

  // 지문: 줄 단위로 나눠서 단을 넘김
  function placeSet(u) {
    const hd = u.querySelector('.sethd');
    const lines = [...u.querySelector('.box').children];
    const make = (first) => {
      const w = document.createElement('div'); w.className = 'u set';
      if (first) { w.appendChild(hd); if (u.dataset.mid) { w.style.marginTop = u.style.marginTop; w.dataset.mid = 1; } }
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
      if (over() && l.classList.contains('brk')) {
        // [A] 묶음이 단 끝에 걸리면 괄호를 둘로 나눠 다음 단으로 이어지게(위쪽은 아래 끝 열림, 아래쪽은 위 끝 열림)
        const inner = [...l.querySelector('.bx2 > div').children];
        const lab = l.querySelector('.lab2').textContent;
        b.removeChild(l);
        const mk = (cls) => { const g = document.createElement('div'); g.className = 'ln brk ' + cls;
          g.innerHTML = '<div class="bx2"><span class="lab2"></span><span class="br2"></span><div></div></div>'; return g; };
        const g1 = mk('open-b'); b.appendChild(g1);
        const box1 = g1.querySelector('.bx2 > div');
        let k = 0;
        while (k < inner.length) { box1.appendChild(inner[k]); if (over()) { box1.removeChild(inner[k]); break; } k++; }
        if (k >= 2 && k < inner.length) {
          b.classList.add('open'); nextCol(); [w, b] = make(false);
          const g2 = mk('open-t'); b.appendChild(g2);
          const box2 = g2.querySelector('.bx2 > div');
          inner.slice(k).forEach(x => box2.appendChild(x));
          const big = (inner.length - k) >= k ? g2 : g1, small = big === g1 ? g2 : g1;
          big.querySelector('.lab2').textContent = lab;
          small.querySelector('.lab2').textContent = lab; small.querySelector('.lab2').style.visibility = 'hidden';
          i++; continue;
        }
        // 나눌 수 없으면 원래대로 묶음째 다음 단으로
        b.removeChild(g1); inner.forEach(x => l.querySelector('.bx2 > div').appendChild(x));
        b.appendChild(l);
      }
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
    if (u.classList.contains('colbrk')) { if (!empty()) nextCol(); col.dataset.forced = 1; return; }
    if (u.classList.contains('memo')) { colIdx = 2; col = null; nextCol(); const pg = pages[pages.length - 1]; pg.querySelector('.cols').innerHTML = '<div class="memo"><span>MEMO</span></div>'; pg.querySelector('.cols').classList.add('one'); return; }
    if (u.classList.contains('set')) {
      if (!empty()) {
        // 단에 공간이 많이 남으면(1/3 이상) 남는 공간의 절반을 띄우고 그 자리에서 지문 시작, 아니면 다음 단
        const last = col.lastElementChild;
        const used = last.offsetTop + last.offsetHeight + parseFloat(getComputedStyle(last).marginBottom);
        const left = col.clientHeight - used;
        if (left >= col.clientHeight / 3) { u.style.marginTop = (left / 2 - parseFloat(getComputedStyle(last).marginBottom)) + 'px'; u.dataset.mid = 1; }
        else nextCol();
      }
      return placeSet(u);
    }
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
  // 문제 쪽: 단 첫머리는 첫 줄부터, 남는 공간의 절반을 문항 사이에 고르게 나눔
  document.querySelectorAll('.col').forEach(c => {
    const kids = [...c.children];
    if (!kids.length) return;
    if (!kids[0].classList.contains('toc')) kids[0].style.marginTop = '0';
    if (c.querySelector('.ex, .toc, .extitle, [data-mid]')) return;
    const used = kids[kids.length - 1].offsetTop + kids[kids.length - 1].offsetHeight - kids[0].offsetTop;
    const left = c.clientHeight - used;
    const gaps = kids.length - 1;
    if (gaps < 1 || left <= 0) return;
    const add = left / 2 / gaps;
    kids.slice(0, -1).forEach(k => { k.style.marginBottom = (parseFloat(getComputedStyle(k).marginBottom) + add) + 'px'; });
  });
  window.PAGES = pages.length;
  document.body.dataset.done = '1';
})();
