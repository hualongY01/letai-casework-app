import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api";

type OCRPage = {
  ocr_page_uid: string;
  source_uid: string;
  page_number: number;
  page_image_path: string;
  page_image_hash: string;
  ocr_engine: string;
};

type OCRBlock = {
  ocr_block_uid: string;
  ocr_page_uid: string;
  text: string;
  confidence: number;
  bbox_json: string;
};

type EvidenceSpan = {
  evidence_uid: string;
  source_uid: string;
  chunk_uid: string | null;
  ocr_page_uid: string | null;
  excerpt: string;
  locator_json: string;
  confidence: number;
};

type BBox = {
  x: number;
  y: number;
  width: number;
  height: number;
};

type ImageSize = {
  naturalWidth: number;
  naturalHeight: number;
  renderedWidth: number;
  renderedHeight: number;
};

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init);
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

function parseBox(value: string): BBox | null {
  try {
    const parsed = JSON.parse(value) as Partial<BBox>;
    if (
      typeof parsed.x === "number" &&
      typeof parsed.y === "number" &&
      typeof parsed.width === "number" &&
      typeof parsed.height === "number"
    ) {
      return {
        x: parsed.x,
        y: parsed.y,
        width: parsed.width,
        height: parsed.height,
      };
    }
  } catch {
    return null;
  }
  return null;
}

function findEvidenceForBlock(block: OCRBlock, evidence: EvidenceSpan[]): EvidenceSpan | undefined {
  return evidence.find((item) => {
    if (item.ocr_page_uid !== block.ocr_page_uid) return false;
    try {
      const locator = JSON.parse(item.locator_json) as { ocr_block_uid?: string };
      return locator.ocr_block_uid === block.ocr_block_uid;
    } catch {
      return false;
    }
  });
}

function App() {
  const [pages, setPages] = useState<OCRPage[]>([]);
  const [blocks, setBlocks] = useState<OCRBlock[]>([]);
  const [evidence, setEvidence] = useState<EvidenceSpan[]>([]);
  const [selectedPageUid, setSelectedPageUid] = useState<string>("");
  const [selectedBlockUid, setSelectedBlockUid] = useState<string>("");
  const [imageSize, setImageSize] = useState<ImageSize | null>(null);
  const [status, setStatus] = useState("Loading");

  async function refresh() {
    setStatus("Loading");
    try {
      const [nextPages, nextBlocks, nextEvidence] = await Promise.all([
        fetchJson<OCRPage[]>("/ocr-pages"),
        fetchJson<OCRBlock[]>("/ocr-blocks"),
        fetchJson<EvidenceSpan[]>("/evidence"),
      ]);
      setPages(nextPages);
      setBlocks(nextBlocks);
      setEvidence(nextEvidence);
      setSelectedPageUid((current) => current || nextPages[0]?.ocr_page_uid || "");
      setStatus(nextPages.length ? "Loaded" : "No OCR pages. Import a file and run render-pages first.");
    } catch (error) {
      setStatus(`Load failed: ${error instanceof Error ? error.message : "unknown error"}`);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  const selectedPage = pages.find((page) => page.ocr_page_uid === selectedPageUid);
  const pageBlocks = useMemo(
    () => blocks.filter((block) => block.ocr_page_uid === selectedPageUid),
    [blocks, selectedPageUid],
  );
  const selectedBlock = pageBlocks.find((block) => block.ocr_block_uid === selectedBlockUid);

  async function runOCR() {
    if (!selectedPage) return;
    setStatus("Running OCR");
    try {
      await fetchJson(`/ocr-pages/${selectedPage.ocr_page_uid}/run-ocr`, { method: "POST" });
      await refresh();
      setStatus("OCR completed");
    } catch (error) {
      setStatus(`OCR failed: ${error instanceof Error ? error.message : "unknown error"}`);
    }
  }

  async function createCandidate(block: OCRBlock) {
    const matchedEvidence = findEvidenceForBlock(block, evidence);
    if (!matchedEvidence || !selectedPage) {
      setStatus("No evidence matched this OCR block");
      return;
    }
    try {
      await fetchJson("/candidates", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          source_uid: selectedPage.source_uid,
          evidence_uid: matchedEvidence.evidence_uid,
          original_candidate_text: block.text,
          proposed_fact_text: block.text,
          fact_type: "ocr_observation",
          tags: ["ocr", "pending_review"],
          llm_model: null,
          prompt_version: null,
        }),
      });
      setStatus("Candidate fact created");
    } catch (error) {
      setStatus(`Candidate creation failed: ${error instanceof Error ? error.message : "unknown error"}`);
    }
  }

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <h1>Letai Factbase</h1>
        <nav>
          <button>Import</button>
          <button className="active">OCR Review</button>
          <button>Candidate Facts</button>
          <button>Confirmed FC</button>
          <button>Fact Gateway</button>
        </nav>
        <section className="page-list">
          <h2>OCR Pages</h2>
          {pages.map((page) => (
            <button
              className={page.ocr_page_uid === selectedPageUid ? "active" : ""}
              key={page.ocr_page_uid}
              onClick={() => {
                setSelectedPageUid(page.ocr_page_uid);
                setSelectedBlockUid("");
                setImageSize(null);
              }}
            >
              {page.source_uid} · p{page.page_number}
            </button>
          ))}
        </section>
      </aside>
      <section className="review-layout">
        <header className="review-header">
          <div>
            <h2>OCR Highlight Review</h2>
            <p>{status}</p>
          </div>
          <div className="header-actions">
            <button onClick={() => void refresh()}>Refresh</button>
            <button disabled={!selectedPage} onClick={() => void runOCR()}>
              Run OCR
            </button>
          </div>
        </header>
        <div className="review-grid">
          <div className="page-preview" aria-label="OCR page preview">
            {selectedPage ? (
              <div className="image-stage">
                <img
                  alt={`OCR page ${selectedPage.page_number}`}
                  className="page-image"
                  src={`${API_BASE}/ocr-pages/${selectedPage.ocr_page_uid}/image`}
                  onLoad={(event) => {
                    const image = event.currentTarget;
                    setImageSize({
                      naturalWidth: image.naturalWidth,
                      naturalHeight: image.naturalHeight,
                      renderedWidth: image.clientWidth,
                      renderedHeight: image.clientHeight,
                    });
                  }}
                />
                {imageSize &&
                  pageBlocks.map((block) => {
                    const box = parseBox(block.bbox_json);
                    if (!box) return null;
                    const scaleX = imageSize.renderedWidth / imageSize.naturalWidth;
                    const scaleY = imageSize.renderedHeight / imageSize.naturalHeight;
                    const selected = block.ocr_block_uid === selectedBlockUid;
                    return (
                      <button
                        aria-label={`OCR block ${block.text}`}
                        className={`bbox ${selected ? "selected" : ""}`}
                        key={block.ocr_block_uid}
                        onClick={() => setSelectedBlockUid(block.ocr_block_uid)}
                        style={{
                          left: box.x * scaleX,
                          top: box.y * scaleY,
                          width: box.width * scaleX,
                          height: box.height * scaleY,
                        }}
                      />
                    );
                  })}
              </div>
            ) : (
              <div className="empty-state">No page available</div>
            )}
          </div>
          <aside className="candidate-panel">
            <h3>OCR Blocks</h3>
            {pageBlocks.length === 0 && <p className="muted">No OCR blocks on the selected page.</p>}
            {pageBlocks.map((block) => {
              const selected = block.ocr_block_uid === selectedBlockUid;
              const matchedEvidence = findEvidenceForBlock(block, evidence);
              return (
                <article
                  className={`candidate-card ${selected ? "selected" : ""}`}
                  key={block.ocr_block_uid}
                  onClick={() => setSelectedBlockUid(block.ocr_block_uid)}
                >
                  <div className="status">{block.confidence.toFixed(2)}</div>
                  <p>{block.text}</p>
                  <dl>
                    <dt>Block</dt>
                    <dd>{block.ocr_block_uid}</dd>
                    <dt>Evidence</dt>
                    <dd>{matchedEvidence?.evidence_uid ?? "Not matched"}</dd>
                  </dl>
                  <div className="actions">
                    <button onClick={() => void createCandidate(block)}>Create candidate fact</button>
                  </div>
                </article>
              );
            })}
            {selectedBlock && (
              <section className="selection-detail">
                <h4>Current Selection</h4>
                <p>{selectedBlock.text}</p>
              </section>
            )}
          </aside>
        </div>
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
