/**
 * Handcode Studio — Frontend Logic & Visual Plotter Engine
 */

let state = {
  templates: {},
  currentTemplateId: "kokuyo_camlin_small",
  pages: [],
  currentPageIndex: 0,
  zoom: 1.0,
  inkColor: "#1c4595",
  availablePorts: [],
  writtenWordCutoff: 0,
  writtenPrefixText: ""
};

// DOM Elements
const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("fileInput");
const textInput = document.getElementById("textInput");
const charCount = document.getElementById("charCount");
const wordCount = document.getElementById("wordCount");
const btnSampleText = document.getElementById("btnSampleText");

const templateSelect = document.getElementById("templateSelect");
const customConfigDetails = document.getElementById("customConfigDetails");
const cfgWidth = document.getElementById("cfgWidth");
const cfgHeight = document.getElementById("cfgHeight");
const cfgMarginLeft = document.getElementById("cfgMarginLeft");
const cfgMarginRight = document.getElementById("cfgMarginRight");
const cfgMarginTop = document.getElementById("cfgMarginTop");
const cfgMarginBottom = document.getElementById("cfgMarginBottom");
const cfgLineSpacing = document.getElementById("cfgLineSpacing");
const cfgShowRuled = document.getElementById("cfgShowRuled");
const cfgShowMargin = document.getElementById("cfgShowMargin");

const styleSelect = document.getElementById("styleSelect");
const biasSlider = document.getElementById("biasSlider");
const biasVal = document.getElementById("biasVal");
const fontSizeInput = document.getElementById("fontSizeInput");
const fontSizeVal = document.getElementById("fontSizeVal");
const btnRender = document.getElementById("btnRender");
const btnRenderTop = document.getElementById("btnRenderTop");

const chkShowRuled = document.getElementById("chkShowRuled");
const chkShowTravel = document.getElementById("chkShowTravel");
const chkShowPaper = document.getElementById("chkShowPaper");

const paperSheet = document.getElementById("paperSheet");
const plotSvg = document.getElementById("plotSvg");
const ruledLinesGroup = document.getElementById("ruledLinesGroup");
const travelPath = document.getElementById("travelPath");
const writtenPath = document.getElementById("writtenPath");
const drawPath = document.getElementById("drawPath");

const pageIndicator = document.getElementById("pageIndicator");
const btnPrevPage = document.getElementById("btnPrevPage");
const btnNextPage = document.getElementById("btnNextPage");
const pageTabsContainer = document.getElementById("pageTabsContainer");

const btnZoomIn = document.getElementById("btnZoomIn");
const btnZoomOut = document.getElementById("btnZoomOut");
const btnZoomFit = document.getElementById("btnZoomFit");
const zoomLevel = document.getElementById("zoomLevel");

const statWords = document.getElementById("statWords");
const statDistance = document.getElementById("statDistance");
const statTime = document.getElementById("statTime");
const statPages = document.getElementById("statPages");

const btnDownloadSvg = document.getElementById("btnDownloadSvg");
const btnDownloadGcodePage = document.getElementById("btnDownloadGcodePage");
const btnDownloadGcodeAll = document.getElementById("btnDownloadGcodeAll");
const btnStreamPlot = document.getElementById("btnStreamPlot");

const machineStatusPill = document.getElementById("machineStatusPill");
const machineStatusText = document.getElementById("machineStatusText");
const btnRefreshPorts = document.getElementById("btnRefreshPorts");

// Modal
const streamModal = document.getElementById("streamModal");
const btnCloseModal = document.getElementById("btnCloseModal");
const streamProgressFill = document.getElementById("streamProgressFill");
const streamProgressPct = document.getElementById("streamProgressPct");
const streamLinesCounter = document.getElementById("streamLinesCounter");
const streamLogBox = document.getElementById("streamLogBox");
const btnStreamPause = document.getElementById("btnStreamPause");
const btnStreamStop = document.getElementById("btnStreamStop");

// Machine Jog & Test Controls
const btnJogYPlus = document.getElementById("btnJogYPlus");
const btnJogYMinus = document.getElementById("btnJogYMinus");
const btnJogXPlus = document.getElementById("btnJogXPlus");
const btnJogXMinus = document.getElementById("btnJogXMinus");
const btnZeroOrigin = document.getElementById("btnZeroOrigin");
const btnTestPenDown = document.getElementById("btnTestPenDown");
const btnTestPenUp = document.getElementById("btnTestPenUp");
const btnUnlockMachine = document.getElementById("btnUnlockMachine");

// Live Pen Tip Marker Elements
const chkShowPenTip = document.getElementById("chkShowPenTip");
const livePenMarker = document.getElementById("livePenMarker");
const penTipCore = document.getElementById("penTipCore");
const penMarkerTagText = document.getElementById("penMarkerTagText");
const liveCoordsText = document.getElementById("liveCoordsText");
const livePenBadge = document.getElementById("livePenBadge");
const chkTouchToMove = document.getElementById("chkTouchToMove");
const touchTargetRipple = document.getElementById("touchTargetRipple");
const chkLabRecordFlip = document.getElementById("chkLabRecordFlip");
const chkLabRecordFlipToolbar = document.getElementById("chkLabRecordFlipToolbar");
const chkResumeFromTouch = document.getElementById("chkResumeFromTouch");
const chkResumeFromTouchToolbar = document.getElementById("chkResumeFromTouchToolbar");

// Paper Continuation & Marking Elements
const continuationBadge = document.getElementById("continuationBadge");
const btnMarkSelection = document.getElementById("btnMarkSelection");
const btnMarkUpToCursor = document.getElementById("btnMarkUpToCursor");
const btnMarkAllWritten = document.getElementById("btnMarkAllWritten");
const btnClearMarked = document.getElementById("btnClearMarked");
const inputStartWord = document.getElementById("inputStartWord");
const btnWordStepMinus = document.getElementById("btnWordStepMinus");
const btnWordStepPlus = document.getElementById("btnWordStepPlus");
const continuationTotalWords = document.getElementById("continuationTotalWords");
const chkShowWritten = document.getElementById("chkShowWritten");
const chkSkipWritten = document.getElementById("chkSkipWritten");

let liveRenderDebounceTimer = null;

function triggerLiveRender(delayMs = 400) {
  if (liveRenderDebounceTimer) {
    clearTimeout(liveRenderDebounceTimer);
    liveRenderDebounceTimer = null;
  }
  const text = textInput.value.trim();
  if (!text) {
    clearCanvas();
    return;
  }
  if (delayMs <= 0) {
    renderHandwriting();
  } else {
    liveRenderDebounceTimer = setTimeout(() => {
      renderHandwriting();
    }, delayMs);
  }
}

// Initialize
document.addEventListener("DOMContentLoaded", async () => {
  setupEventListeners();
  await loadTemplates();
  await checkPorts();
  // Start with clean empty editor and blank Kokuyo Camlin notebook sheet
  textInput.value = "";
  updateTextCounters();
  displayBlankPage();
  startLiveMachinePoller();
});

function setupEventListeners() {
  // File Ingestion
  dropzone.addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", handleFileUpload);
  dropzone.addEventListener("dragover", (e) => { e.preventDefault(); dropzone.classList.add("dragover"); });
  dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));
  dropzone.addEventListener("drop", handleFileDrop);

  // Live Text Typing
  textInput.addEventListener("input", () => {
    updateTextCounters();
    triggerLiveRender(400);
  });
  btnSampleText.addEventListener("click", loadSampleText);

  // Template change
  templateSelect.addEventListener("change", () => {
    handleTemplateChange();
  });

  // Live update paper bounds and re-render when custom inputs change
  [cfgWidth, cfgHeight, cfgMarginLeft, cfgMarginRight, cfgMarginTop, cfgMarginBottom, cfgLineSpacing].forEach(el => {
    el.addEventListener("input", () => {
      displayBlankPage();
      triggerLiveRender(350);
    });
  });
  cfgShowRuled.addEventListener("change", () => {
    displayBlankPage();
    if (state.pages && state.pages.length > 0) displayPage(state.currentPageIndex);
  });
  cfgShowMargin.addEventListener("change", () => {
    displayBlankPage();
    if (state.pages && state.pages.length > 0) displayPage(state.currentPageIndex);
  });

  // Live Style & Sliders
  styleSelect.addEventListener("change", () => {
    triggerLiveRender(0); // Instant update on style change!
  });
  biasSlider.addEventListener("input", () => {
    biasVal.textContent = biasSlider.value;
    triggerLiveRender(250); // Live update as slider moves
  });
  fontSizeInput.addEventListener("input", () => {
    fontSizeVal.textContent = fontSizeInput.value;
    triggerLiveRender(250); // Live update as slider moves
  });

  // Explicit Render Buttons
  if (btnRender) btnRender.addEventListener("click", () => triggerLiveRender(0));
  if (btnRenderTop) btnRenderTop.addEventListener("click", () => triggerLiveRender(0));

  window.addEventListener("resize", fitToViewport);

  // Page Nav
  btnPrevPage.addEventListener("click", () => switchPage(state.currentPageIndex - 1));
  btnNextPage.addEventListener("click", () => switchPage(state.currentPageIndex + 1));

  // Toggles
  chkShowRuled.addEventListener("change", () => {
    ruledLinesGroup.style.display = chkShowRuled.checked ? "block" : "none";
  });
  chkShowTravel.addEventListener("change", () => {
    travelPath.style.display = chkShowTravel.checked ? "block" : "none";
  });
  chkShowPaper.addEventListener("change", () => {
    paperSheet.classList.toggle("textured", chkShowPaper.checked);
  });

  // Zoom
  btnZoomIn.addEventListener("click", () => setZoom(state.zoom + 0.15));
  btnZoomOut.addEventListener("click", () => setZoom(state.zoom - 0.15));
  btnZoomFit.addEventListener("click", fitToViewport);

  // Downloads
  btnDownloadSvg.addEventListener("click", downloadSvg);
  btnDownloadGcodePage.addEventListener("click", () => downloadGcode(state.currentPageIndex));
  btnDownloadGcodeAll.addEventListener("click", () => downloadGcode(null));

  // Machine Streaming & Hardware Controls
  btnStreamPlot.addEventListener("click", openStreamingModal);
  btnCloseModal.addEventListener("click", () => streamModal.setAttribute("hidden", ""));
  btnRefreshPorts.addEventListener("click", checkPorts);

  if (btnJogYPlus) btnJogYPlus.addEventListener("click", () => sendMachineJog(0, 10));
  if (btnJogYMinus) btnJogYMinus.addEventListener("click", () => sendMachineJog(0, -10));
  if (btnJogXPlus) btnJogXPlus.addEventListener("click", () => sendMachineJog(10, 0));
  if (btnJogXMinus) btnJogXMinus.addEventListener("click", () => sendMachineJog(-10, 0));
  if (btnZeroOrigin) btnZeroOrigin.addEventListener("click", sendMachineZero);
  if (btnTestPenDown) btnTestPenDown.addEventListener("click", () => sendMachinePen(true));
  if (btnTestPenUp) btnTestPenUp.addEventListener("click", () => sendMachinePen(false));
  if (btnUnlockMachine) btnUnlockMachine.addEventListener("click", sendMachineUnlock);

  const btnFlipPenCmds = document.getElementById("btnFlipPenCmds");
  if (btnFlipPenCmds) {
    btnFlipPenCmds.addEventListener("click", () => {
      const downEl = document.getElementById("penDownCmd");
      const upEl = document.getElementById("penUpCmd");
      if (downEl && upEl) {
        const tmp = downEl.value;
        downEl.value = upEl.value;
        upEl.value = tmp;
        if (btnTestPenDown) btnTestPenDown.textContent = `Pen Down (${downEl.value.split(" ")[0]})`;
        if (btnTestPenUp) btnTestPenUp.textContent = `Pen Up (${upEl.value.split(" ")[0]})`;
      }
    });
  }

  if (btnStreamPause) btnStreamPause.addEventListener("click", toggleStreamPause);
  if (btnStreamStop) btnStreamStop.addEventListener("click", stopStream);

  if (chkShowPenTip) {
    chkShowPenTip.addEventListener("change", () => {
      if (livePenMarker) {
        livePenMarker.style.display = chkShowPenTip.checked ? "block" : "none";
      }
    });
  }
  const chkInvertY = document.getElementById("chkInvertY");
  if (chkInvertY) {
    chkInvertY.addEventListener("change", fetchCurrentMachineStatus);
  }

  if (chkLabRecordFlip && chkLabRecordFlipToolbar) {
    chkLabRecordFlip.addEventListener("change", () => {
      chkLabRecordFlipToolbar.checked = chkLabRecordFlip.checked;
      fetchCurrentMachineStatus();
    });
    chkLabRecordFlipToolbar.addEventListener("change", () => {
      chkLabRecordFlip.checked = chkLabRecordFlipToolbar.checked;
      fetchCurrentMachineStatus();
    });
  } else if (chkLabRecordFlip) {
    chkLabRecordFlip.addEventListener("change", fetchCurrentMachineStatus);
  }

  if (chkResumeFromTouch && chkResumeFromTouchToolbar) {
    chkResumeFromTouch.addEventListener("change", () => {
      chkResumeFromTouchToolbar.checked = chkResumeFromTouch.checked;
      fetchCurrentMachineStatus();
    });
    chkResumeFromTouchToolbar.addEventListener("change", () => {
      chkResumeFromTouch.checked = chkResumeFromTouchToolbar.checked;
      fetchCurrentMachineStatus();
    });
  }

  if (chkTouchToMove) {
    chkTouchToMove.addEventListener("change", () => {
      if (paperSheet) {
        paperSheet.classList.toggle("touch-mode-active", chkTouchToMove.checked);
      }
    });
  }

  // Touch / Click Coordination on Virtual Page
  if (plotSvg) {
    plotSvg.addEventListener("click", handlePaperTouchMove);
    plotSvg.addEventListener("touchend", handlePaperTouchMove);
  }

  // Card Section Scroll Controls & Quick Jump Navigation
  setupCardScrollControls();
  setupSectionJumpNavigation();

  // Paper Continuation & Written Text Marking Controls
  if (btnMarkSelection) btnMarkSelection.addEventListener("click", markSelectionAsWritten);
  if (btnMarkUpToCursor) btnMarkUpToCursor.addEventListener("click", markUpToCursorAsWritten);
  if (btnMarkAllWritten) btnMarkAllWritten.addEventListener("click", markAllAsWritten);
  if (btnClearMarked) btnClearMarked.addEventListener("click", clearMarkedWritten);

  if (btnWordStepMinus) btnWordStepMinus.addEventListener("click", () => setStartWordCutoff(state.writtenWordCutoff - 1));
  if (btnWordStepPlus) btnWordStepPlus.addEventListener("click", () => setStartWordCutoff(state.writtenWordCutoff + 1));

  if (inputStartWord) {
    inputStartWord.addEventListener("change", () => {
      const v = parseInt(inputStartWord.value);
      if (!isNaN(v)) setStartWordCutoff(v - 1);
    });
    inputStartWord.addEventListener("input", () => {
      const v = parseInt(inputStartWord.value);
      if (!isNaN(v) && v >= 1) setStartWordCutoff(v - 1);
    });
  }

  if (chkShowWritten) {
    chkShowWritten.addEventListener("change", () => {
      if (writtenPath) {
        writtenPath.style.display = chkShowWritten.checked ? "block" : "none";
      }
    });
  }

  if (chkSkipWritten) {
    chkSkipWritten.addEventListener("change", () => {
      updateContinuationUI();
    });
  }
}

function setupCardScrollControls() {
  const cardsOrder = ["card1", "card2", "card3", "card4"];

  document.querySelectorAll(".btn-card-scroll").forEach(btn => {
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      const targetId = btn.getAttribute("data-target");
      const direction = btn.getAttribute("data-action");
      const currentCardId = btn.getAttribute("data-card") || targetId?.replace("Body", "");
      const targetEl = document.getElementById(targetId);
      const sidebar = document.querySelector(".sidebar");
      const scrollAmount = 90;

      if (!targetEl) return;

      const cardIdx = cardsOrder.indexOf(currentCardId);
      const canScrollEl = targetEl.scrollHeight > targetEl.clientHeight + 4;
      const isAtTop = targetEl.scrollTop <= 6;
      const isAtBottom = (targetEl.scrollTop + targetEl.clientHeight) >= (targetEl.scrollHeight - 6);

      if (direction === "up") {
        if (canScrollEl && !isAtTop) {
          // Scroll inside card body
          targetEl.scrollBy({ top: -scrollAmount, behavior: "smooth" });
        } else {
          // Navigate to previous card or top of sidebar
          if (cardIdx > 0) {
            const prevCard = document.getElementById(cardsOrder[cardIdx - 1]);
            if (prevCard) {
              prevCard.scrollIntoView({ behavior: "smooth", block: "start" });
              prevCard.classList.add("card-highlight");
              setTimeout(() => prevCard.classList.remove("card-highlight"), 800);
            }
          } else if (sidebar) {
            sidebar.scrollTo({ top: 0, behavior: "smooth" });
          }
        }
      } else if (direction === "down") {
        if (canScrollEl && !isAtBottom) {
          // Scroll inside card body
          targetEl.scrollBy({ top: scrollAmount, behavior: "smooth" });
        } else {
          // Navigate to next card or bottom of sidebar
          if (cardIdx !== -1 && cardIdx < cardsOrder.length - 1) {
            const nextCard = document.getElementById(cardsOrder[cardIdx + 1]);
            if (nextCard) {
              nextCard.scrollIntoView({ behavior: "smooth", block: "start" });
              nextCard.classList.add("card-highlight");
              setTimeout(() => nextCard.classList.remove("card-highlight"), 800);
            }
          } else if (sidebar) {
            sidebar.scrollTo({ top: sidebar.scrollHeight, behavior: "smooth" });
          }
        }
      }
    });
  });
}

function setupSectionJumpNavigation() {
  document.querySelectorAll(".btn-jump-section").forEach(btn => {
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      const cardId = btn.getAttribute("data-jump");
      const cardEl = document.getElementById(cardId);
      if (cardEl) {
        cardEl.scrollIntoView({ behavior: "smooth", block: "start" });
        cardEl.classList.add("card-highlight");
        setTimeout(() => cardEl.classList.remove("card-highlight"), 800);
      }
    });
  });
}

async function loadTemplates() {
  try {
    const res = await fetch("/api/templates");
    const data = await res.json();
    if (data.success) {
      state.templates = data.templates;
      const initialTpl = state.templates[state.currentTemplateId] || Object.values(data.templates)[0];
      applyTemplateToForm(initialTpl);
      displayBlankPage(initialTpl);
    }
  } catch (err) {
    console.error("Failed to load templates:", err);
  }
}

function handleTemplateChange() {
  const selected = templateSelect.value;
  state.currentTemplateId = selected;
  if (selected === "custom") {
    customConfigDetails.open = true;
  } else if (state.templates[selected]) {
    applyTemplateToForm(state.templates[selected]);
  }
  displayBlankPage(getActiveTemplateConfig());
  if (textInput.value.trim()) {
    triggerLiveRender(0);
  }
}

function displayBlankPage(t) {
  if (!t) t = getActiveTemplateConfig();
  const w = t.width || 155;
  const h = t.height || 190;

  paperSheet.style.width = `${w * 3.2}px`;
  paperSheet.style.height = `${h * 3.2}px`;
  plotSvg.setAttribute("viewBox", `0 0 ${w} ${h}`);

  ruledLinesGroup.innerHTML = "";
  if (t.show_ruled_lines !== false) {
    let current_y = t.margin_top;
    while (current_y <= (h - t.margin_bottom + 0.1)) {
      const el = document.createElementNS("http://www.w3.org/2000/svg", "line");
      el.setAttribute("x1", "0");
      el.setAttribute("y1", current_y);
      el.setAttribute("x2", w);
      el.setAttribute("y2", current_y);
      el.setAttribute("stroke", t.ruled_line_color || "rgba(80, 140, 200, 0.45)");
      el.setAttribute("stroke-width", "0.25");
      ruledLinesGroup.appendChild(el);
      current_y += t.line_spacing;
    }
    if (t.margin_top >= t.line_spacing) {
      const el = document.createElementNS("http://www.w3.org/2000/svg", "line");
      el.setAttribute("x1", "0");
      el.setAttribute("y1", t.margin_top - t.line_spacing * 0.8);
      el.setAttribute("x2", w);
      el.setAttribute("y2", t.margin_top - t.line_spacing * 0.8);
      el.setAttribute("stroke", t.margin_line_color || "rgba(225, 75, 75, 0.65)");
      el.setAttribute("stroke-width", "0.35");
      ruledLinesGroup.appendChild(el);
    }
  }

  if (t.show_margin_line !== false) {
    const el = document.createElementNS("http://www.w3.org/2000/svg", "line");
    el.setAttribute("x1", t.margin_left);
    el.setAttribute("y1", "0");
    el.setAttribute("x2", t.margin_left);
    el.setAttribute("y2", h);
    el.setAttribute("stroke", t.margin_line_color || "rgba(225, 75, 75, 0.65)");
    el.setAttribute("stroke-width", "0.35");
    ruledLinesGroup.appendChild(el);
  }
  fitToViewport();
}

function applyTemplateToForm(t) {
  if (!t) return;
  cfgWidth.value = t.width;
  cfgHeight.value = t.height;
  cfgMarginLeft.value = t.margin_left;
  cfgMarginRight.value = t.margin_right;
  cfgMarginTop.value = t.margin_top;
  cfgMarginBottom.value = t.margin_bottom;
  cfgLineSpacing.value = t.line_spacing;
  cfgShowRuled.checked = t.show_ruled_lines !== false;
  cfgShowMargin.checked = t.show_margin_line !== false;
  fontSizeInput.value = t.font_size || 5.2;
  fontSizeVal.textContent = fontSizeInput.value;
}

function getActiveTemplateConfig() {
  return {
    id: templateSelect.value,
    name: templateSelect.value === "custom" ? "Custom Notebook" : (state.templates[templateSelect.value]?.name || "Custom"),
    width: parseFloat(cfgWidth.value),
    height: parseFloat(cfgHeight.value),
    margin_left: parseFloat(cfgMarginLeft.value),
    margin_right: parseFloat(cfgMarginRight.value),
    margin_top: parseFloat(cfgMarginTop.value),
    margin_bottom: parseFloat(cfgMarginBottom.value),
    line_spacing: parseFloat(cfgLineSpacing.value),
    show_ruled_lines: cfgShowRuled.checked,
    show_margin_line: cfgShowMargin.checked,
    font_size: parseFloat(fontSizeInput.value),
    word_spacing: 3.2,
    ruled_line_color: "rgba(80, 140, 200, 0.45)",
    margin_line_color: "rgba(225, 75, 75, 0.65)"
  };
}

function updateTextCounters() {
  const text = textInput.value;
  charCount.textContent = `${text.length} characters`;
  const words = text.trim() ? text.trim().split(/\s+/).length : 0;
  wordCount.textContent = `${words} words`;
}

function loadSampleText() {
  textInput.value = 
`Kokuyo Camlin Notebook Plotting Experiment:
This handwriting machine uses an Arduino Uno with CH340C.
The neural network translates each letter into fluid human strokes.
Single line spacing is calibrated precisely at 8.0 mm so every line
rests gently on the notebook rule.

Whether plotting poems, class notes, or formal letters,
each character flows naturally with authentic cursive variations.`;
  updateTextCounters();
  triggerLiveRender(0);
}

async function handleFileUpload(e) {
  const file = e.target.files[0];
  if (file) await uploadAndExtract(file);
}

async function handleFileDrop(e) {
  e.preventDefault();
  dropzone.classList.remove("dragover");
  const file = e.dataTransfer.files[0];
  if (file) await uploadAndExtract(file);
}

async function uploadAndExtract(file) {
  const formData = new FormData();
  formData.append("file", file);

  dropzone.innerHTML = `<div class="drop-icon">⏳</div><p class="drop-text">Extracting text from <strong>${file.name}</strong>...</p>`;

  try {
    const res = await fetch("/api/extract", { method: "POST", body: formData });
    const data = await res.json();
    if (data.success && data.text) {
      textInput.value = data.text;
      updateTextCounters();
      renderHandwriting();
    } else {
      alert("Text extraction failed: " + (data.error || "No text extracted"));
    }
  } catch (err) {
    alert("Extraction error: " + err);
  } finally {
    dropzone.innerHTML = `
      <input type="file" id="fileInput" accept=".png,.jpg,.jpeg,.webp,.pdf,.docx,.txt,.md" hidden>
      <div class="drop-icon">📄</div>
      <p class="drop-text"><strong>Click or Drop file here</strong></p>
      <span class="drop-hint">Images (OCR), PDFs, Word (.docx), or Text</span>
    `;
    document.getElementById("fileInput").addEventListener("change", handleFileUpload);
  }
}

function setRenderButtonsState(isLoading) {
  const buttons = [document.getElementById("btnRender"), document.getElementById("btnRenderTop")].filter(Boolean);
  buttons.forEach(btn => {
    btn.disabled = isLoading;
    btn.innerHTML = isLoading 
      ? `<span class="btn-icon">⏳</span> Synthesizing Strokes...`
      : `<span class="btn-icon">⚡</span> Render Handwriting`;
  });
}

async function renderHandwriting() {
  const text = textInput.value.trim();
  if (!text) {
    clearCanvas();
    return;
  }

  setRenderButtonsState(true);

  const tpl = getActiveTemplateConfig();
  const payload = {
    text: text,
    template_id: templateSelect.value,
    custom_template: tpl,
    style: parseInt(styleSelect.value),
    bias: parseFloat(biasSlider.value),
    font_size: parseFloat(fontSizeInput.value)
  };

  try {
    const res = await fetch("/api/render", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: jsonStringify(payload)
    });
    const data = await res.json();
    if (data.success) {
      state.pages = data.pages;
      const totalWords = getTotalWordsCount();
      if (state.writtenWordCutoff > totalWords) {
        state.writtenWordCutoff = totalWords;
      }
      state.currentPageIndex = 0;
      updatePageNav();
      displayPage(0);
      updateMetrics();
      fitToViewport();
    } else {
      alert("Render error: " + data.error);
    }
  } catch (err) {
    console.error("Render failed:", err);
  } finally {
    setRenderButtonsState(false);
  }
}

// Paper Continuation & Written Marking Logic
function buildSvgPathD(points) {
  if (!points || points.length === 0) return "";
  const cmds = [];
  let inDraw = false;
  for (let i = 0; i < points.length; i++) {
    const pt = points[i];
    const x = Number(pt[0]).toFixed(2);
    const y = Number(pt[1]).toFixed(2);
    const penup = Number(pt[2]);

    if (penup > 0) {
      if (inDraw) inDraw = false;
      cmds.push(`M ${x} ${y}`);
    } else {
      if (!inDraw) {
        cmds.push(`M ${x} ${y}`);
        inDraw = true;
      } else {
        cmds.push(`L ${x} ${y}`);
      }
    }
  }
  return cmds.join(" ");
}

function getTotalWordsCount() {
  if (!state.pages || state.pages.length === 0) {
    const text = textInput ? textInput.value.trim() : "";
    return text ? text.split(/\s+/).length : 0;
  }
  let total = 0;
  for (const p of state.pages) {
    if (p.words) {
      total += p.words.length;
    } else {
      total += (p.words_count || 0);
    }
  }
  return total;
}

function getPageWrittenStrokeEnd(page, cutoffWordIdx) {
  if (!page || !page.words || page.words.length === 0 || !page.strokes_points) return 0;
  if (cutoffWordIdx <= 0) return 0;

  let maxStrokeEnd = 0;
  for (let i = 0; i < page.words.length; i++) {
    const w = page.words[i];
    if (w.word_index < cutoffWordIdx) {
      if (w.stroke_end > maxStrokeEnd) {
        maxStrokeEnd = w.stroke_end;
      }
    }
  }
  return Math.min(maxStrokeEnd, page.strokes_points.length);
}

function updateContinuationUI() {
  const totalWords = getTotalWordsCount();
  const cutoff = state.writtenWordCutoff || 0;

  if (continuationTotalWords) {
    continuationTotalWords.textContent = `of ${totalWords} words`;
  }

  if (inputStartWord) {
    inputStartWord.min = 1;
    inputStartWord.max = Math.max(1, totalWords + 1);
    inputStartWord.value = Math.min(cutoff + 1, totalWords + 1);
  }

  if (continuationBadge) {
    if (totalWords === 0) {
      continuationBadge.textContent = "0 on paper • All pending";
      continuationBadge.className = "continuation-badge";
    } else if (cutoff <= 0) {
      continuationBadge.textContent = `0 on paper • All pending (${totalWords} words)`;
      continuationBadge.className = "continuation-badge";
    } else if (cutoff >= totalWords) {
      continuationBadge.textContent = `${cutoff}/${totalWords} on paper • All written!`;
      continuationBadge.className = "continuation-badge all-written";
    } else {
      continuationBadge.textContent = `${cutoff}/${totalWords} on paper • Next: #${cutoff + 1}`;
      continuationBadge.className = "continuation-badge partial-written";
    }
  }
}

function setStartWordCutoff(num) {
  const totalWords = getTotalWordsCount();
  const clamped = Math.max(0, Math.min(totalWords, Math.floor(num)));
  state.writtenWordCutoff = clamped;

  if (state.pages && state.pages.length > 0) {
    displayPage(state.currentPageIndex);
  } else {
    updateContinuationUI();
  }
}

function markSelectionAsWritten() {
  if (!textInput) return;
  const selStart = textInput.selectionStart;
  const selEnd = textInput.selectionEnd;
  const text = textInput.value;

  if (selEnd > 0) {
    const targetCharIdx = (selEnd > selStart) ? selEnd : selStart;
    const textUpToSel = text.slice(0, targetCharIdx).trim();
    const wordCount = textUpToSel ? textUpToSel.split(/\s+/).length : 0;
    setStartWordCutoff(wordCount);
  } else {
    markUpToCursorAsWritten();
  }
}

function markUpToCursorAsWritten() {
  if (!textInput) return;
  const cursor = textInput.selectionStart || 0;
  const text = textInput.value;
  const textUpToCursor = text.slice(0, cursor).trim();
  const wordCount = textUpToCursor ? textUpToCursor.split(/\s+/).length : 0;
  setStartWordCutoff(wordCount);
}

function markAllAsWritten() {
  const total = getTotalWordsCount();
  setStartWordCutoff(total);
}

function clearMarkedWritten() {
  setStartWordCutoff(0);
}

function filterPagesForContinuation(pages) {
  if (!chkSkipWritten || !chkSkipWritten.checked || state.writtenWordCutoff <= 0) {
    return pages;
  }
  return pages.map(page => {
    const cutoff = getPageWrittenStrokeEnd(page, state.writtenWordCutoff);
    const totalPts = page.strokes_points ? page.strokes_points.length : 0;
    if (cutoff <= 0) {
      return page;
    }
    if (cutoff >= totalPts) {
      return {
        ...page,
        strokes_points: []
      };
    }
    return {
      ...page,
      strokes_points: page.strokes_points.slice(cutoff)
    };
  });
}

function displayPage(pageIdx) {
  if (!state.pages || state.pages.length === 0 || pageIdx < 0 || pageIdx >= state.pages.length) return;
  state.currentPageIndex = pageIdx;
  const page = state.pages[pageIdx];

  const w = page.width;
  const h = page.height;

  // Set paper dimensions in mm (scale 1mm = 3.7795px approx for screen, or direct mm viewBox)
  paperSheet.style.width = `${w * 3.2}px`;
  paperSheet.style.height = `${h * 3.2}px`;
  plotSvg.setAttribute("viewBox", `0 0 ${w} ${h}`);

  // Ruled Lines
  ruledLinesGroup.innerHTML = "";
  if (page.show_ruled_lines && page.ruled_lines) {
    // Horizontal lines
    page.ruled_lines.horizontal.forEach(line => {
      const el = document.createElementNS("http://www.w3.org/2000/svg", "line");
      el.setAttribute("x1", line.x1);
      el.setAttribute("y1", line.y1);
      el.setAttribute("x2", line.x2);
      el.setAttribute("y2", line.y2);
      el.setAttribute("stroke", page.ruled_line_color);
      el.setAttribute("stroke-width", "0.25");
      ruledLinesGroup.appendChild(el);
    });

    // Top Header Line
    if (page.ruled_lines.header_line) {
      const hl = page.ruled_lines.header_line;
      const el = document.createElementNS("http://www.w3.org/2000/svg", "line");
      el.setAttribute("x1", hl.x1);
      el.setAttribute("y1", hl.y1);
      el.setAttribute("x2", hl.x2);
      el.setAttribute("y2", hl.y2);
      el.setAttribute("stroke", page.margin_line_color);
      el.setAttribute("stroke-width", "0.35");
      ruledLinesGroup.appendChild(el);
    }
  }

  // Margin Line
  if (page.show_margin_line && page.ruled_lines?.vertical_margin) {
    const vm = page.ruled_lines.vertical_margin;
    const el = document.createElementNS("http://www.w3.org/2000/svg", "line");
    el.setAttribute("x1", vm.x1);
    el.setAttribute("y1", vm.y1);
    el.setAttribute("x2", vm.x2);
    el.setAttribute("y2", vm.y2);
    el.setAttribute("stroke", page.margin_line_color);
    el.setAttribute("stroke-width", "0.35");
    ruledLinesGroup.appendChild(el);
  }

  // Paths (Continuation & Marking Support)
  const cutoffWordIdx = state.writtenWordCutoff || 0;
  const writtenStrokeEnd = getPageWrittenStrokeEnd(page, cutoffWordIdx);
  const totalStrokes = page.strokes_points ? page.strokes_points.length : 0;

  if (writtenStrokeEnd <= 0) {
    if (writtenPath) writtenPath.setAttribute("d", "");
    drawPath.setAttribute("d", page.draw_path || "");
  } else if (writtenStrokeEnd >= totalStrokes) {
    if (writtenPath) writtenPath.setAttribute("d", page.draw_path || "");
    drawPath.setAttribute("d", "");
  } else {
    const writtenPts = page.strokes_points.slice(0, writtenStrokeEnd);
    const pendingPts = page.strokes_points.slice(writtenStrokeEnd);
    if (writtenPath) writtenPath.setAttribute("d", buildSvgPathD(writtenPts));
    drawPath.setAttribute("d", buildSvgPathD(pendingPts));
  }

  drawPath.setAttribute("stroke", state.inkColor);
  if (writtenPath) {
    const showWritten = !chkShowWritten || chkShowWritten.checked;
    writtenPath.style.display = showWritten ? "block" : "none";
  }
  travelPath.setAttribute("d", page.travel_path || "");

  updateContinuationUI();

  // Update nav buttons
  updatePageNav();
}

function updatePageNav() {
  const total = state.pages.length || 1;
  const current = state.currentPageIndex + 1;
  pageIndicator.textContent = `Page ${current} of ${total}`;
  btnPrevPage.disabled = state.currentPageIndex <= 0;
  btnNextPage.disabled = state.currentPageIndex >= total - 1;

  // Tabs
  pageTabsContainer.innerHTML = "";
  state.pages.forEach((_, idx) => {
    const btn = document.createElement("button");
    btn.className = `page-tab-btn ${idx === state.currentPageIndex ? "active" : ""}`;
    btn.textContent = `P${idx + 1}`;
    btn.addEventListener("click", () => switchPage(idx));
    pageTabsContainer.appendChild(btn);
  });
}

function switchPage(idx) {
  if (idx >= 0 && idx < state.pages.length) {
    displayPage(idx);
  }
}

function updateMetrics() {
  let totalW = 0, totalDist = 0, totalTime = 0;
  state.pages.forEach(p => {
    totalW += p.words_count;
    totalDist += p.draw_distance_mm;
    totalTime += p.est_draw_time_min;
  });

  statWords.textContent = totalW;
  statDistance.textContent = `${(totalDist / 1000.0).toFixed(2)} m`;
  statTime.textContent = `${totalTime.toFixed(1)} min`;
  statPages.textContent = state.pages.length;
}

function clearCanvas() {
  state.pages = [];
  state.writtenWordCutoff = 0;
  if (writtenPath) writtenPath.setAttribute("d", "");
  drawPath.setAttribute("d", "");
  travelPath.setAttribute("d", "");
  displayBlankPage();
  updateContinuationUI();
  statWords.textContent = "0";
  statDistance.textContent = "0.0 m";
  statTime.textContent = "0.0 min";
  statPages.textContent = "1";
  pageIndicator.textContent = "Page 1 of 1";
  pageTabsContainer.innerHTML = "";
}

// Zoom Handlers
function setZoom(val) {
  state.zoom = Math.max(0.4, Math.min(2.5, val));
  paperSheet.style.transform = `scale(${state.zoom})`;
  zoomLevel.textContent = `${Math.round(state.zoom * 100)}%`;
}

function fitToViewport() {
  const vp = document.getElementById("canvasViewport");
  if (!vp || !paperSheet) {
    setZoom(1.0);
    return;
  }
  const tpl = getActiveTemplateConfig();
  const paperW = (tpl.width || 155) * 3.2;
  const paperH = (tpl.height || 190) * 3.2;
  const pad = 50;
  const availW = Math.max(100, vp.clientWidth - pad);
  const availH = Math.max(100, vp.clientHeight - pad);
  const scaleX = availW / paperW;
  const scaleY = availH / paperH;
  const fitScale = Math.min(scaleX, scaleY, 1.25);
  setZoom(Math.max(0.4, Math.round(fitScale * 100) / 100));
}

// Downloads
function downloadSvg() {
  if (!state.pages[state.currentPageIndex]) return;
  const svgData = plotSvg.outerHTML;
  const blob = new Blob([svgData], { type: "image/svg+xml;charset=utf-8" });
  triggerDownload(blob, `handwriting_page_${state.currentPageIndex + 1}.svg`);
}

async function downloadGcode(pageIndex) {
  if (!state.pages || state.pages.length === 0) return;
  const penMode = document.querySelector('input[name="penMode"]:checked').value;
  const penDownCmd = document.getElementById("penDownCmd")?.value || "M5";
  const penUpCmd = document.getElementById("penUpCmd")?.value || "M3 S90";
  const feedDraw = parseInt(document.getElementById("feedDraw").value);
  const feedTravel = parseInt(document.getElementById("feedTravel").value);
  const invertY = document.getElementById("chkInvertY")?.checked || false;
  const flipLabRecord = chkLabRecordFlip?.checked || false;
  const resumeFromTouch = chkResumeFromTouch ? chkResumeFromTouch.checked : true;
  const returnToOrigin = !resumeFromTouch;

  const pagesToUse = filterPagesForContinuation(state.pages);

  const payload = {
    pages: pagesToUse,
    page_index: pageIndex,
    pen_mode: penMode,
    pen_down_cmd: penDownCmd,
    pen_up_cmd: penUpCmd,
    feed_draw: feedDraw,
    feed_travel: feedTravel,
    invert_y: invertY,
    flip_lab_record: flipLabRecord,
    return_to_origin: returnToOrigin,
    resume_from_current: resumeFromTouch
  };

  try {
    const res = await fetch("/api/gcode", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: jsonStringify(payload)
    });
    const data = await res.json();
    if (data.success && data.gcode) {
      const fn = pageIndex !== null ? `plot_page_${pageIndex + 1}.nc` : `plot_all_pages.nc`;
      const blob = new Blob([data.gcode], { type: "text/plain" });
      triggerDownload(blob, fn);
    }
  } catch (err) {
    alert("G-code generation error: " + err);
  }
}

function triggerDownload(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// Port & Hardware Status
async function checkPorts() {
  try {
    const res = await fetch("/api/ports");
    const data = await res.json();
    const ports = data.ports || [];
    state.availablePorts = ports;

    const dot = machineStatusPill.querySelector(".status-dot");
    if (ports.includes("/dev/ttyUSB0")) {
      dot.className = "status-dot connected";
      machineStatusText.textContent = "Arduino Connected (/dev/ttyUSB0)";
      btnStreamPlot.disabled = false;
    } else if (ports.length > 0) {
      dot.className = "status-dot connected";
      machineStatusText.textContent = `Port: ${ports[0]}`;
      btnStreamPlot.disabled = false;
    } else {
      dot.className = "status-dot disconnected";
      machineStatusText.textContent = "Machine Offline (Laptop Mode)";
    }
  } catch (err) {
    console.error("Port check failed:", err);
  }
}

// Machine Streaming Modal
async function openStreamingModal() {
  if (!state.pages || state.pages.length === 0) {
    alert("Please render handwriting first!");
    return;
  }

  const pagesToUse = filterPagesForContinuation(state.pages);
  const hasStrokes = pagesToUse.some(p => p.strokes_points && p.strokes_points.length > 0);
  if (!hasStrokes) {
    alert("All text is currently marked as already written on paper! Reset marks or append new text before plotting.");
    return;
  }

  // If current page is completely written, jump to first page with unwritten strokes
  let targetPageIndex = state.currentPageIndex;
  const currPageStrokes = pagesToUse[targetPageIndex]?.strokes_points?.length || 0;
  if (currPageStrokes === 0) {
    const nextUnwrittenIdx = pagesToUse.findIndex(p => p.strokes_points && p.strokes_points.length > 0);
    if (nextUnwrittenIdx !== -1) {
      targetPageIndex = nextUnwrittenIdx;
      switchPage(targetPageIndex);
    }
  }

  const resumeFromTouch = chkResumeFromTouch ? chkResumeFromTouch.checked : true;
  const returnToOrigin = !resumeFromTouch;

  streamModal.removeAttribute("hidden");
  const resumeMsg = resumeFromTouch 
    ? "<p style='color:#38bdf8;'>🎯 Resuming directly from current / touched position (Origin return skipped)</p>"
    : "<p>Homing to (0,0) origin before plotting...</p>";
  streamLogBox.innerHTML = "<p>Connecting to controller...</p>" + resumeMsg;

  // Generate G-code for target page
  const penMode = document.querySelector('input[name="penMode"]:checked').value;
  const penDownCmd = document.getElementById("penDownCmd")?.value || "M5";
  const penUpCmd = document.getElementById("penUpCmd")?.value || "M3 S90";
  const feedDraw = parseInt(document.getElementById("feedDraw").value);
  const feedTravel = parseInt(document.getElementById("feedTravel").value);
  const invertY = document.getElementById("chkInvertY")?.checked || false;
  const flipLabRecord = chkLabRecordFlip?.checked || false;

  const payload = {
    pages: pagesToUse,
    page_index: targetPageIndex,
    pen_mode: penMode,
    pen_down_cmd: penDownCmd,
    pen_up_cmd: penUpCmd,
    feed_draw: feedDraw,
    feed_travel: feedTravel,
    invert_y: invertY,
    flip_lab_record: flipLabRecord,
    return_to_origin: returnToOrigin,
    resume_from_current: resumeFromTouch
  };

  const res = await fetch("/api/gcode", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: jsonStringify(payload)
  });
  const data = await res.json();

  if (!data.gcode) {
    streamLogBox.innerHTML += "<p style='color:red'>Failed to build G-code</p>";
    return;
  }

  // Start Stream
  const streamRes = await fetch("/api/stream/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: jsonStringify({ gcode: data.gcode, port: "/dev/ttyUSB0" })
  });
  const streamData = await streamRes.json();

  if (streamData.success) {
    pollStreamProgress();
  } else {
    streamLogBox.innerHTML += `<p style='color:red'>Stream start failed: ${streamData.message}</p>`;
  }
}

let pollInterval = null;
let streamIsPaused = false;

function pollStreamProgress() {
  if (pollInterval) clearInterval(pollInterval);
  streamIsPaused = false;
  btnStreamPause.textContent = "Pause";
  btnStreamPause.className = "btn btn-warning";

  pollInterval = setInterval(async () => {
    try {
      const res = await fetch("/api/stream/status");
      const data = await res.json();
      const s = data.status;

      streamProgressFill.style.width = `${s.progress_percent}%`;
      streamProgressPct.textContent = `${s.progress_percent}%`;
      streamLinesCounter.textContent = `Line ${s.sent_lines} of ${s.total_lines}`;

      if (s.logs && s.logs.length > 0) {
        streamLogBox.innerHTML = s.logs.map(l => `<p>${l}</p>`).join("");
        streamLogBox.scrollTop = streamLogBox.scrollHeight;
      }

      if (s) {
        updateLivePenMarker(s.wpos, s.mpos, s.pen_down, s.machine_state);
      }

      if (!s.is_streaming) {
        clearInterval(pollInterval);
        pollInterval = null;
        if (s.total_lines > 0 && s.sent_lines >= s.total_lines) {
          streamProgressPct.textContent = "100% (Completed)";
          // Auto-mark written text upon completion of plot job
          const totalWords = getTotalWordsCount();
          if (totalWords > 0) {
            setStartWordCutoff(totalWords);
          }
        }
      }
    } catch (e) {
      console.error(e);
    }
  }, 400);
}

async function toggleStreamPause() {
  try {
    if (!streamIsPaused) {
      await fetch("/api/stream/pause", { method: "POST" });
      btnStreamPause.textContent = "Resume";
      btnStreamPause.className = "btn btn-success";
      streamIsPaused = true;
    } else {
      await fetch("/api/stream/resume", { method: "POST" });
      btnStreamPause.textContent = "Pause";
      btnStreamPause.className = "btn btn-warning";
      streamIsPaused = false;
    }
  } catch (err) {
    console.error("Pause/resume error:", err);
  }
}

async function stopStream() {
  if (confirm("Are you sure you want to stop and reset the plotting job?")) {
    try {
      await fetch("/api/stream/stop", { method: "POST" });
      if (pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
      }
      streamProgressPct.textContent = "Aborted";
      btnStreamPause.textContent = "Pause";
      btnStreamPause.className = "btn btn-warning";
      streamIsPaused = false;
      fetchCurrentMachineStatus();
    } catch (err) {
      console.error("Stop stream error:", err);
    }
  }
}

async function sendMachineJog(dx, dy) {
  try {
    const res = await fetch("/api/machine/jog", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ dx, dy, feed: 1500 })
    });
    const data = await res.json();
    if (data.status) {
      updateLivePenMarker(data.status.wpos, data.status.mpos, data.status.pen_down, data.status.machine_state);
    }
    if (!data.success) {
      alert("Jog command failed. Check connection or 12V power!");
    }
  } catch (err) {
    alert("Machine jog error: " + err);
  }
}

async function sendMachinePen(down) {
  try {
    const penDownCmd = document.getElementById("penDownCmd")?.value || "M5";
    const penUpCmd = document.getElementById("penUpCmd")?.value || "M3 S90";
    const res = await fetch("/api/machine/pen", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ down, pen_down_cmd: penDownCmd, pen_up_cmd: penUpCmd })
    });
    const data = await res.json();
    if (data.status) {
      updateLivePenMarker(data.status.wpos, data.status.mpos, data.status.pen_down, data.status.machine_state);
    }
    if (!data.success) {
      alert("Pen test command failed.");
    }
  } catch (err) {
    alert("Pen test error: " + err);
  }
}

async function sendMachineZero() {
  try {
    const res = await fetch("/api/machine/zero", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({})
    });
    const data = await res.json();
    if (data.status) {
      updateLivePenMarker(data.status.wpos, data.status.mpos, data.status.pen_down, data.status.machine_state);
    }
    if (data.success) {
      alert("Origin set to current position (0, 0, 0)");
    }
  } catch (err) {
    alert("Zero origin error: " + err);
  }
}

async function sendMachineUnlock() {
  try {
    const res = await fetch("/api/machine/unlock", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({})
    });
    const data = await res.json();
    if (data.status) {
      updateLivePenMarker(data.status.wpos, data.status.mpos, data.status.pen_down, data.status.machine_state);
    }
    if (data.success) {
      alert("GRBL Alarm cleared ($X) — Controller Unlocked!");
    }
  } catch (err) {
    alert("Unlock machine error: " + err);
  }
}

// Live Pen Tip Position Tracker
function updateLivePenMarker(wpos, mpos, penDown, machineState) {
  if (!livePenMarker || !chkShowPenTip) return;

  if (!chkShowPenTip.checked) {
    livePenMarker.style.display = "none";
    return;
  }

  const invertY = document.getElementById("chkInvertY")?.checked || false;
  const flipLabRecord = chkLabRecordFlip?.checked || false;
  const tpl = getActiveTemplateConfig();
  const pageW = (tpl && tpl.width) ? tpl.width : 155.0;
  const pageH = (tpl && tpl.height) ? tpl.height : 190.0;

  // Use Work Position (relative to Zero origin) if available, fallback to MPos
  const pos = (wpos && wpos.length >= 2) ? wpos : ((mpos && mpos.length >= 2) ? mpos : [0.0, 0.0]);
  const x = pos[0];
  const y = pos[1];

  // SVG coordinate system
  const svgX = flipLabRecord ? (pageW - x) : x;
  const svgY = flipLabRecord ? (invertY ? y : (pageH - y)) : (invertY ? (pageH - y) : y);

  // Position SVG marker
  livePenMarker.setAttribute("transform", `translate(${svgX.toFixed(2)}, ${svgY.toFixed(2)})`);
  livePenMarker.style.display = "block";

  // Coordinate text badge on SVG
  if (penMarkerTagText) {
    penMarkerTagText.textContent = `X:${x.toFixed(1)} Y:${y.toFixed(1)}`;
  }

  // Live Position HUD in Card 4
  if (liveCoordsText) {
    const labTag = flipLabRecord ? " [Lab 180°]" : "";
    const resumeTag = (chkResumeFromTouch && chkResumeFromTouch.checked) ? " • 🎯 Direct Resume" : "";
    liveCoordsText.textContent = `X: ${x.toFixed(2)} mm, Y: ${y.toFixed(2)} mm${labTag}${resumeTag}`;
  }

  // Pen Down indicator
  if (penDown) {
    livePenMarker.classList.add("pen-down-active");
    if (livePenBadge) {
      livePenBadge.textContent = "DOWN";
      livePenBadge.className = "live-pen-badge down";
    }
  } else {
    livePenMarker.classList.remove("pen-down-active");
    if (livePenBadge) {
      livePenBadge.textContent = "UP";
      livePenBadge.className = "live-pen-badge up";
    }
  }
}

async function fetchCurrentMachineStatus() {
  try {
    const res = await fetch("/api/stream/status");
    const data = await res.json();
    if (data && data.status) {
      const s = data.status;
      updateLivePenMarker(s.wpos, s.mpos, s.pen_down, s.machine_state);
    }
  } catch (e) {
    // Quiet offline
  }
}

let liveMachinePollerTimer = null;
function startLiveMachinePoller() {
  if (liveMachinePollerTimer) clearInterval(liveMachinePollerTimer);
  fetchCurrentMachineStatus();
  liveMachinePollerTimer = setInterval(fetchCurrentMachineStatus, 450);
}

// Touch Coordination: Millimeter coordinate mapping & Machine Motion
function getSvgCoordinates(evt) {
  if (!plotSvg) return null;
  const pt = plotSvg.createSVGPoint();
  if (evt.changedTouches && evt.changedTouches.length > 0) {
    pt.x = evt.changedTouches[0].clientX;
    pt.y = evt.changedTouches[0].clientY;
  } else if (evt.touches && evt.touches.length > 0) {
    pt.x = evt.touches[0].clientX;
    pt.y = evt.touches[0].clientY;
  } else {
    pt.x = evt.clientX;
    pt.y = evt.clientY;
  }
  const ctm = plotSvg.getScreenCTM();
  if (!ctm) return null;
  const svgP = pt.matrixTransform(ctm.inverse());
  return { x: svgP.x, y: svgP.y };
}

async function handlePaperTouchMove(evt) {
  if (!chkTouchToMove || !chkTouchToMove.checked) return;

  const coords = getSvgCoordinates(evt);
  if (!coords) return;

  const tpl = getActiveTemplateConfig();
  const pageW = tpl.width || 155.0;
  const pageH = tpl.height || 190.0;

  // Clamp within paper bounds
  const svgX = Math.max(0, Math.min(pageW, Math.round(coords.x * 10) / 10));
  const svgY = Math.max(0, Math.min(pageH, Math.round(coords.y * 10) / 10));

  // Trigger ripple animation at target
  showTouchRipple(svgX, svgY);

  // Map to Machine Coordinates with Bed Invert support and Lab Record Mode
  const invertY = document.getElementById("chkInvertY")?.checked || false;
  const flipLabRecord = chkLabRecordFlip?.checked || false;

  const machineX = flipLabRecord ? (pageW - svgX) : svgX;
  const machineY = flipLabRecord ? (invertY ? svgY : (pageH - svgY)) : (invertY ? (pageH - svgY) : svgY);

  await sendMachineMoveTo(machineX, machineY);
}

function showTouchRipple(x, y) {
  const ripple = document.getElementById("touchTargetRipple");
  if (!ripple) return;
  ripple.setAttribute("cx", x.toFixed(2));
  ripple.setAttribute("cy", y.toFixed(2));
  ripple.classList.remove("animate-ripple");
  void ripple.offsetWidth; // Force reflow
  ripple.classList.add("animate-ripple");
}

async function sendMachineMoveTo(x, y) {
  try {
    const feed = parseInt(document.getElementById("feedTravel")?.value) || 3500;
    const res = await fetch("/api/machine/moveto", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ x, y, feed })
    });
    const data = await res.json();
    if (data.status) {
      updateLivePenMarker(data.status.wpos, data.status.mpos, data.status.pen_down, data.status.machine_state);
    }
  } catch (err) {
    console.error("Machine MoveTo error:", err);
  }
}

function jsonStringify(obj) {
  return JSON.stringify(obj);
}
