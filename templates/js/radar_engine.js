    // ========================================================
    // 多股六大維度量化雷達圖互動引擎 (Multi-Stock Radar Engine)
    // ========================================================
    const rawRadarComparison = {{ radar_comparison_json | safe }};
    const rawDeliberationData = {{ deliberation_verdicts_json | safe }};

    let radarChartInstance = null;
    const radarColorPalette = [
      '#10b981', // Emerald
      '#06b6d4', // Cyan
      '#f59e0b', // Amber
      '#ec4899', // Pink
      '#8b5cf6', // Violet
      '#3b82f6'  // Blue
    ];

    let selectedRadarSymbols = [];
    const allRadarStocks = (rawRadarComparison && rawRadarComparison.stocks) ? rawRadarComparison.stocks : [];

    function initRadarStockSelection() {
      if (!allRadarStocks || allRadarStocks.length === 0) return;
      
      const preferred = ['2330', '2454', 'NVDA', '2317'];
      const found = preferred.filter(sym => allRadarStocks.some(s => s.symbol === sym));
      if (found.length >= 2) {
        selectedRadarSymbols = found.slice(0, 3);
      } else {
        selectedRadarSymbols = allRadarStocks.slice(0, 3).map(s => s.symbol);
      }
    }

    function renderRadarChips() {
      const container = document.getElementById("radarChipContainer");
      if (!container || !allRadarStocks) return;

      const searchTerm = (document.getElementById("radarSearchInput")?.value || "").trim().toLowerCase();
      container.innerHTML = "";

      allRadarStocks.forEach(stock => {
        const sym = stock.symbol;
        const name = stock.name || sym;
        const isSelected = selectedRadarSymbols.includes(sym);
        
        if (searchTerm && !sym.toLowerCase().includes(searchTerm) && !name.toLowerCase().includes(searchTerm)) {
          return;
        }

        const chip = document.createElement("button");
        chip.type = "button";
        chip.onclick = () => toggleRadarStock(sym);
        
        if (isSelected) {
          chip.className = "px-2.5 py-1 text-xs font-bold rounded-lg bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 flex items-center space-x-1.5 shadow-sm transition hover:scale-105";
          chip.innerHTML = `<i class="fa-solid fa-check text-[10px]"></i><span>${sym} ${name}</span>`;
        } else {
          chip.className = "px-2.5 py-1 text-xs font-medium rounded-lg bg-gray-800 text-gray-400 border border-gray-700/80 flex items-center space-x-1.5 hover:text-gray-200 hover:border-gray-600 transition";
          chip.innerHTML = `<i class="fa-solid fa-plus text-[10px] text-gray-500"></i><span>${sym} ${name}</span>`;
        }

        container.appendChild(chip);
      });

      const badge = document.getElementById("selectedRadarBadge");
      if (badge) {
        badge.textContent = `已選取 ${selectedRadarSymbols.length}/6 檔`;
        if (selectedRadarSymbols.length < 2) {
          badge.className = "ml-2.5 px-2.5 py-0.5 text-xs font-bold rounded-full bg-rose-500/20 text-rose-300 border border-rose-500/30";
        } else {
          badge.className = "ml-2.5 px-2.5 py-0.5 text-xs font-bold rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30";
        }
      }
    }

    function filterRadarChips() {
      renderRadarChips();
    }

    function toggleRadarStock(sym) {
      const idx = selectedRadarSymbols.indexOf(sym);
      if (idx >= 0) {
        if (selectedRadarSymbols.length <= 1) {
          alert("至少需保留 1 檔標的進行對比！");
          return;
        }
        selectedRadarSymbols.splice(idx, 1);
      } else {
        if (selectedRadarSymbols.length >= 6) {
          alert("最多同時比對 6 檔標的，請先取消其他標的！");
          return;
        }
        selectedRadarSymbols.push(sym);
      }
      renderRadarChips();
      updateRadarDisplay();
    }

    function clearRadarSelection() {
      selectedRadarSymbols = [];
      renderRadarChips();
      updateRadarDisplay();
    }

    function applyRadarPreset(preset) {
      if (!allRadarStocks) return;
      if (preset === 'core') {
        const core = allRadarStocks.filter(s => s.tier === 'TIER_1_CORE').map(s => s.symbol);
        selectedRadarSymbols = core.length >= 2 ? core.slice(0, 4) : allRadarStocks.slice(0, 3).map(s => s.symbol);
      } else if (preset === 'ai') {
        const aiSyms = ['2317', '2382', '3017', 'NVDA', '2454'];
        selectedRadarSymbols = allRadarStocks.filter(s => aiSyms.includes(s.symbol)).map(s => s.symbol).slice(0, 4);
        if (selectedRadarSymbols.length === 0) selectedRadarSymbols = allRadarStocks.slice(0, 3).map(s => s.symbol);
      } else if (preset === 'top_momentum') {
        const sorted = [...allRadarStocks].sort((a, b) => (b.composite || 0) - (a.composite || 0));
        selectedRadarSymbols = sorted.slice(0, 3).map(s => s.symbol);
      }
      renderRadarChips();
      updateRadarDisplay();
    }

    function updateRadarDisplay() {
      const chartDom = document.getElementById("multiStockRadarChart");
      if (!chartDom || !window.echarts) return;

      if (!radarChartInstance) {
        radarChartInstance = echarts.init(chartDom);
        window.addEventListener("resize", () => radarChartInstance && radarChartInstance.resize());
      }

      const dimensions = (rawRadarComparison && rawRadarComparison.dimensions) ? rawRadarComparison.dimensions : [
        { name: '技術動能', max: 100 },
        { name: '主力籌碼', max: 100 },
        { name: '基本面前瞻', max: 100 },
        { name: '波克夏護城河', max: 100 },
        { name: '風險防禦', max: 100 },
        { name: '多空綜合評分', max: 100 }
      ];

      const activeStocks = allRadarStocks.filter(s => selectedRadarSymbols.includes(s.symbol));

      if (activeStocks.length === 0) {
        radarChartInstance.clear();
        document.getElementById("radarComparisonCards").innerHTML = `
          <div class="p-8 text-center text-gray-500 text-xs">
            <i class="fa-solid fa-arrow-pointer text-xl mb-2 text-gray-600 block"></i>
            請於上方點擊標籤選取欲比對之股票
          </div>
        `;
        return;
      }

      const seriesData = activeStocks.map((s, idx) => {
        const color = radarColorPalette[idx % radarColorPalette.length];
        return {
          name: `${s.symbol} ${s.name}`,
          value: [
            s.technicals || 50,
            s.flows || 50,
            s.fundamentals || 50,
            s.moat || 50,
            s.defense || 50,
            s.composite || 50
          ],
          itemStyle: { color: color },
          lineStyle: { width: 2.5, color: color },
          areaStyle: { color: color, opacity: 0.22 },
          symbolSize: 4
        };
      });

      const isMobile = window.innerWidth < 640;

      const option = {
        backgroundColor: 'transparent',
        tooltip: {
          trigger: 'item',
          backgroundColor: 'rgba(17, 24, 39, 0.95)',
          borderColor: 'rgba(255, 255, 255, 0.1)',
          textStyle: { color: '#f3f4f6', fontSize: 12 },
          formatter: function(params) {
            const vals = params.value;
            return `
              <div class="font-bold border-b border-gray-700 pb-1 mb-1 text-emerald-400">${params.name}</div>
              <div class="text-[11px] space-y-0.5">
                <div>技術動能: <span class="font-bold text-white">${vals[0]}</span></div>
                <div>主力籌碼: <span class="font-bold text-white">${vals[1]}</span></div>
                <div>基本面前瞻: <span class="font-bold text-white">${vals[2]}</span></div>
                <div>波克夏護城河: <span class="font-bold text-white">${vals[3]}</span></div>
                <div>風險防禦: <span class="font-bold text-white">${vals[4]}</span></div>
                <div>多空綜合評分: <span class="font-bold text-amber-300">${vals[5]}</span></div>
              </div>
            `;
          }
        },
        legend: {
          bottom: 0,
          type: isMobile ? 'scroll' : 'plain',
          textStyle: { color: '#9ca3af', fontSize: isMobile ? 10 : 11 },
          itemGap: isMobile ? 8 : 14,
          data: activeStocks.map(s => `${s.symbol} ${s.name}`)
        },
        radar: {
          indicator: dimensions.map(d => ({ name: d.name, max: 100 })),
          shape: 'polygon',
          radius: isMobile ? '60%' : '74%',
          center: ['50%', isMobile ? '46%' : '48%'],
          splitNumber: 4,
          axisName: {
            color: '#cbd5e1',
            fontSize: isMobile ? 10 : 11,
            fontWeight: 600,
            borderRadius: 3,
            padding: [2, 4]
          },
          splitArea: {
            areaStyle: {
              color: ['rgba(30, 41, 59, 0.4)', 'rgba(15, 23, 42, 0.6)']
            }
          },
          axisLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.2)' } },
          splitLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.2)' } }
        },
        series: [{
          type: 'radar',
          data: seriesData
        }]
      };

      radarChartInstance.setOption(option, true);
      renderComparisonCards(activeStocks);
    }

    function renderComparisonCards(stocks) {
      const container = document.getElementById("radarComparisonCards");
      if (!container) return;
      container.innerHTML = "";

      stocks.forEach((s, idx) => {
        const color = radarColorPalette[idx % radarColorPalette.length];
        const delib = rawDeliberationData ? rawDeliberationData[s.symbol] : null;
        const actionBadge = delib ? delib.action : (s.composite >= 75 ? '🚀 順勢進攻' : (s.composite >= 60 ? '☕ 逢低潛伏' : '⏳ 耐心等待'));
        const isCore = s.tier === 'TIER_1_CORE';

        const card = document.createElement("div");
        card.className = "bg-gray-900/80 rounded-xl p-3.5 border border-gray-800 space-y-2 hover:border-gray-700 transition";
        card.style.borderLeft = `4px solid ${color}`;

        const strengthsHtml = (s.strengths || []).map(str => `
          <span class="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] bg-emerald-950/60 text-emerald-300 border border-emerald-800">
            <i class="fa-solid fa-arrow-trend-up mr-1 text-[8px]"></i>${str}
          </span>
        `).join('') || '<span class="text-[10px] text-gray-500">無特殊警示</span>';

        const weaknessesHtml = (w_arr = s.weaknesses || []).map(w => `
          <span class="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] bg-rose-950/60 text-rose-300 border border-rose-800">
            <i class="fa-solid fa-triangle-exclamation mr-1 text-[8px]"></i>${w}
          </span>
        `).join('');

        card.innerHTML = `
          <div class="flex items-center justify-between">
            <div class="flex items-center space-x-2">
              <span class="font-extrabold text-sm text-white">${s.symbol}</span>
              <span class="text-xs text-gray-300 font-medium">${s.name}</span>
              <span class="text-[10px] px-1.5 py-0.2 rounded font-semibold ${isCore ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30' : 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'}">
                ${isCore ? '👑 核心' : '⚡ 動量'}
              </span>
            </div>
            <div class="flex items-center space-x-1.5">
              <span class="text-[10px] font-bold px-2 py-0.5 rounded bg-gray-800 text-gray-200 border border-gray-700">
                ${actionBadge}
              </span>
              <span class="text-xs font-black px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                ${s.composite} 分
              </span>
            </div>
          </div>

          <!-- 六維評分迷你進度條 -->
          <div class="grid grid-cols-3 gap-2 pt-1 text-[10px]">
            <div class="bg-gray-800/60 px-2 py-1 rounded">
              <div class="flex justify-between text-gray-400"><span>技術動能</span><span class="font-bold text-white">${s.technicals}</span></div>
              <div class="w-full bg-gray-700 h-1 rounded-full mt-1 overflow-hidden"><div class="bg-emerald-400 h-full" style="width: ${s.technicals}%"></div></div>
            </div>
            <div class="bg-gray-800/60 px-2 py-1 rounded">
              <div class="flex justify-between text-gray-400"><span>主力籌碼</span><span class="font-bold text-white">${s.flows}</span></div>
              <div class="w-full bg-gray-700 h-1 rounded-full mt-1 overflow-hidden"><div class="bg-cyan-400 h-full" style="width: ${s.flows}%"></div></div>
            </div>
            <div class="bg-gray-800/60 px-2 py-1 rounded">
              <div class="flex justify-between text-gray-400"><span>基本價值</span><span class="font-bold text-white">${s.fundamentals}</span></div>
              <div class="w-full bg-gray-700 h-1 rounded-full mt-1 overflow-hidden"><div class="bg-indigo-400 h-full" style="width: ${s.fundamentals}%"></div></div>
            </div>
            <div class="bg-gray-800/60 px-2 py-1 rounded">
              <div class="flex justify-between text-gray-400"><span>護城河</span><span class="font-bold text-white">${s.moat}</span></div>
              <div class="w-full bg-gray-700 h-1 rounded-full mt-1 overflow-hidden"><div class="bg-amber-400 h-full" style="width: ${s.moat}%"></div></div>
            </div>
            <div class="bg-gray-800/60 px-2 py-1 rounded">
              <div class="flex justify-between text-gray-400"><span>風險防禦</span><span class="font-bold text-white">${s.defense}</span></div>
              <div class="w-full bg-gray-700 h-1 rounded-full mt-1 overflow-hidden"><div class="bg-rose-400 h-full" style="width: ${s.defense}%"></div></div>
            </div>
            <div class="bg-gray-800/60 px-2 py-1 rounded">
              <div class="flex justify-between text-gray-400"><span>綜合評分</span><span class="font-bold text-amber-300">${s.composite}</span></div>
              <div class="w-full bg-gray-700 h-1 rounded-full mt-1 overflow-hidden"><div class="bg-amber-400 h-full" style="width: ${s.composite}%"></div></div>
            </div>
          </div>

          <!-- 亮點標籤 -->
          <div class="flex flex-wrap gap-1.5 pt-1">
            ${strengthsHtml}
            ${weaknessesHtml}
          </div>
        `;
        container.appendChild(card);
      });
    }

    // 頁面加載完成後自動初始化雷達圖
    document.addEventListener("DOMContentLoaded", () => {
      initRadarStockSelection();
      renderRadarChips();
      updateRadarDisplay();
    });
