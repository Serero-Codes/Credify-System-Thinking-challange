import React, { useEffect, useState } from "react";
import { analyzeRepository, getHealth, getSkills } from "./api.js";
import { demoReport } from "./demoReport.js";

const STATUS_LABELS = {
  evidence_found: "Evidence found",
  not_found_in_inspected_files: "Not found in inspected files",
  needs_further_assessment: "Needs further assessment",
  inspection_incomplete: "Inspection incomplete",
};

const CHART_STATUSES = [
  { id: "evidence_found", label: "Evidence found" },
  { id: "needs_further_assessment", label: "Needs further assessment" },
  { id: "not_found_in_inspected_files", label: "Not found in inspected files" },
  { id: "inspection_incomplete", label: "Inspection incomplete" },
];

function safeGitHubUrl(value) {
  try {
    const url = new URL(value);
    if (url.protocol === "https:" && url.hostname === "github.com") {
      return url.href;
    }
  } catch {
    return null;
  }
  return null;
}

function Icon({ name, size = 18 }) {
  const common = {
    width: size,
    height: size,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.8,
    strokeLinecap: "round",
    strokeLinejoin: "round",
    "aria-hidden": true,
  };

  if (name === "arrow") {
    return (
      <svg {...common}>
        <path d="M5 12h14M13 6l6 6-6 6" />
      </svg>
    );
  }
  if (name === "external") {
    return (
      <svg {...common}>
        <path d="M14 4h6v6M20 4l-9 9" />
        <path d="M18 13v6a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h6" />
      </svg>
    );
  }
  if (name === "check") {
    return (
      <svg {...common}>
        <path d="m5 12 4 4L19 6" />
      </svg>
    );
  }
  if (name === "download") {
    return (
      <svg {...common}>
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
        <path d="m7 10 5 5 5-5M12 15V3" />
      </svg>
    );
  }
  if (name === "spark") {
    return (
      <svg {...common}>
        <path d="m12 3 1.7 5.3L19 10l-5.3 1.7L12 17l-1.7-5.3L5 10l5.3-1.7L12 3Z" />
        <path d="m19 16 .8 2.2L22 19l-2.2.8L19 22l-.8-2.2L16 19l2.2-.8L19 16Z" />
      </svg>
    );
  }
  return (
    <svg {...common}>
      <path d="M12 3 4 7v5c0 5 3.4 8 8 9 4.6-1 8-4 8-9V7l-8-4Z" />
      <path d="m9 12 2 2 4-4" />
    </svg>
  );
}

function App() {
  const [skills, setSkills] = useState([]);
  const [maxSkills, setMaxSkills] = useState(8);
  const [repositoryUrl, setRepositoryUrl] = useState("");
  const [selectedSkills, setSelectedSkills] = useState([]);
  const [report, setReport] = useState(null);
  const [isDemo, setIsDemo] = useState(false);
  const [isLoadingSkills, setIsLoadingSkills] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [apiOnline, setApiOnline] = useState(null);
  const [catalogueError, setCatalogueError] = useState("");
  const [formError, setFormError] = useState("");

  async function loadCatalogue() {
    setIsLoadingSkills(true);
    setCatalogueError("");
    const [healthResult, skillsResult] = await Promise.allSettled([
      getHealth(),
      getSkills(),
    ]);

    setApiOnline(healthResult.status === "fulfilled");
    if (skillsResult.status === "rejected") {
      setCatalogueError(skillsResult.reason.message);
      setSkills([]);
    } else {
      const catalogue = skillsResult.value;
      setSkills(catalogue.skills);
      setMaxSkills(catalogue.max_per_request);
    }
    setIsLoadingSkills(false);
  }

  useEffect(() => {
    loadCatalogue();
  }, []);

  const categories = [...new Set(skills.map((skill) => skill.category))];

  function toggleSkill(skillId) {
    if (selectedSkills.includes(skillId)) {
      setSelectedSkills(selectedSkills.filter((id) => id !== skillId));
      setFormError("");
      return;
    }
    if (selectedSkills.length >= maxSkills) {
      setFormError(`Choose no more than ${maxSkills} skills for one report.`);
      return;
    }
    setSelectedSkills([...selectedSkills, skillId]);
    setFormError("");
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setFormError("");

    if (!selectedSkills.length) {
      setFormError("Select at least one skill to review.");
      return;
    }
    if (selectedSkills.length > maxSkills) {
      setFormError(`Choose no more than ${maxSkills} skills for one report.`);
      return;
    }

    setIsSubmitting(true);
    setReport(null);
    setIsDemo(false);
    try {
      const result = await analyzeRepository(repositoryUrl.trim(), selectedSkills);
      setReport(result);
    } catch (error) {
      setFormError(error.message);
    } finally {
      setIsSubmitting(false);
    }
  }

  function showDemo() {
    setReport(demoReport);
    setIsDemo(true);
    setFormError("");
    setSelectedSkills([]);
  }

  function startOver() {
    setReport(null);
    setIsDemo(false);
    setFormError("");
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="#top" aria-label="SkillProof home">
          <span className="brand-mark">S</span>
          <span>skillproof</span>
        </a>
        <nav className="top-nav" aria-label="Main navigation">
          <a href="#how-it-works">How it works</a>
          <a href="#principles">Our principles</a>
        </nav>
        <span className={`api-status ${apiOnline ? "online" : ""}`}>
          <span className="status-dot" />
          {apiOnline === null
            ? "Connecting"
            : apiOnline
              ? "API connected"
              : "API offline"}
        </span>
      </header>

      <main id="top">
        <section className="hero">
          <div className="hero-copy">
            <p className="eyebrow"><span /> A clearer way to show your work</p>
            <h1>Show the work<br />behind your <em>skills.</em></h1>
            <p className="hero-description">
              Turn a public project into a transparent, source-linked evidence
              report. Built to support a human review, never replace one.
            </p>
            <div className="hero-actions">
              <a className="button button-dark" href="#analyze">
                Explore a repository <Icon name="arrow" />
              </a>
              <button className="text-button" type="button" onClick={showDemo}>
                View sample report <Icon name="external" size={16} />
              </button>
            </div>
          </div>
          <aside className="hero-note">
            <div className="note-icon"><Icon name="shield" size={21} /></div>
            <p className="note-kicker">Evidence organiser</p>
            <p className="note-title">Make evidence easier to inspect.</p>
            <p className="note-copy">
              No rankings. No automated decisions. Just useful leads for the
              next conversation.
            </p>
            <div className="note-rule" />
            <p className="note-foot"><span>HUMAN JUDGEMENT</span> stays essential</p>
          </aside>
          <div className="hero-decoration" aria-hidden="true">
            <span>01</span><span>02</span><span>03</span>
          </div>
        </section>

        <section className="workflow" id="how-it-works" aria-label="How it works">
          <div className="workflow-step">
            <span className="step-number">01</span>
            <span className="step-label">Submit repository</span>
            <span className="step-note">A public GitHub URL</span>
          </div>
          <div className="workflow-line" />
          <div className="workflow-step">
            <span className="step-number">02</span>
            <span className="step-label">Select skills</span>
            <span className="step-note">Choose up to {maxSkills}</span>
          </div>
          <div className="workflow-line" />
          <div className="workflow-step">
            <span className="step-number">03</span>
            <span className="step-label">Review evidence</span>
            <span className="step-note">Sources, limits, next steps</span>
          </div>
        </section>

        <section className="workspace" id="analyze">
          {!report ? (
            <div className="form-panel">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">START HERE <span className="heading-rule" /></p>
                  <h2>Bring a project into focus.</h2>
                  <p className="section-intro">
                    We’ll inspect a bounded set of public files for the skills
                    you select.
                  </p>
                </div>
                <span className="step-pill">STEP 01 / 03</span>
              </div>

              {catalogueError && (
                <div className="alert alert-error" role="alert">
                  <div>
                    <strong>Couldn’t load the skill catalogue.</strong>
                    <p>{catalogueError}</p>
                  </div>
                  <button type="button" className="button button-small" onClick={loadCatalogue}>
                    Try again
                  </button>
                </div>
              )}

              <form onSubmit={handleSubmit}>
                <label className="field-label" htmlFor="repository-url">
                  Public GitHub repository
                  <span>Required</span>
                </label>
                <div className="url-field">
                  <span className="url-prefix">github.com /</span>
                  <input
                    id="repository-url"
                    type="url"
                    placeholder="username / repository"
                    value={repositoryUrl}
                    onChange={(event) => {
                      setRepositoryUrl(event.target.value);
                      setFormError("");
                    }}
                    required
                    aria-describedby="repo-hint"
                  />
                  <Icon name="external" size={17} />
                </div>
                <p className="field-hint" id="repo-hint">
                  Enter the full URL, for example https://github.com/owner/repository
                </p>

                <div className="skills-heading">
                  <div>
                    <label className="field-label">What skills should we look for?</label>
                    <p className="field-hint">Choose between 1 and {maxSkills} skills.</p>
                  </div>
                  <span className="selection-count">
                    {selectedSkills.length}<span> / {maxSkills}</span>
                  </span>
                </div>

                {isLoadingSkills ? (
                  <div className="loading-catalogue" role="status">
                    <span className="spinner" /> Loading supported skills…
                  </div>
                ) : (
                  <div className="skill-groups">
                    {categories.map((category) => (
                      <fieldset className="skill-group" key={category}>
                        <legend>{category}</legend>
                        <div className="skill-options">
                          {skills
                            .filter((skill) => skill.category === category)
                            .map((skill) => {
                              const checked = selectedSkills.includes(skill.id);
                              const disabled =
                                !checked && selectedSkills.length >= maxSkills;
                              return (
                                <label
                                  className={`skill-option ${checked ? "selected" : ""} ${disabled ? "disabled" : ""}`}
                                  key={skill.id}
                                  title={skill.description}
                                >
                                  <input
                                    type="checkbox"
                                    checked={checked}
                                    disabled={disabled || isLoadingSkills}
                                    onChange={() => toggleSkill(skill.id)}
                                  />
                                  <span className="checkbox-mark">
                                    {checked && <Icon name="check" size={13} />}
                                  </span>
                                  <span>{skill.name}</span>
                                </label>
                              );
                            })}
                        </div>
                      </fieldset>
                    ))}
                  </div>
                )}

                {formError && <p className="form-error" role="alert">{formError}</p>}

                <div className="form-footer">
                  <button
                    className="button button-primary"
                    type="submit"
                    disabled={isSubmitting || isLoadingSkills || !skills.length}
                  >
                    {isSubmitting ? (
                      <><span className="spinner spinner-light" /> Inspecting repository…</>
                    ) : (
                      <>Generate evidence report <Icon name="arrow" /></>
                    )}
                  </button>
                  <p><Icon name="shield" size={15} /> Your results are not saved.</p>
                </div>
              </form>
            </div>
          ) : (
            <ReportView
              report={report}
              isDemo={isDemo}
              onStartOver={startOver}
            />
          )}

          <aside className="aside-panel" id="principles">
            <p className="eyebrow">WHAT TO EXPECT</p>
            <div className="principle">
              <span className="principle-index">01</span>
              <div>
                <h3>Evidence, not a verdict</h3>
                <p>A detected pattern is a lead to review, not proof of ability.</p>
              </div>
            </div>
            <div className="principle">
              <span className="principle-index">02</span>
              <div>
                <h3>Missing isn’t negative</h3>
                <p>Not found means not found in the files we inspected.</p>
              </div>
            </div>
            <div className="principle">
              <span className="principle-index">03</span>
              <div>
                <h3>People decide what’s next</h3>
                <p>A walkthrough or practical assessment can add useful context.</p>
              </div>
            </div>
            <div className="aside-divider" />
            <p className="aside-caption">
              <Icon name="spark" size={16} />
              A small intervention. A clearer next step.
            </p>
          </aside>
        </section>

        <footer className="page-footer">
          <a className="brand brand-footer" href="#top">
            <span className="brand-mark">S</span><span>skillproof</span>
          </a>
          <p>Project evidence for human review.</p>
          <p className="footer-note">Public repositories · Bounded static analysis · No candidate ranking</p>
        </footer>
      </main>
    </div>
  );
}

function ReportView({ report, isDemo, onStartOver }) {
  const [isPdfLoading, setIsPdfLoading] = useState(false);
  const [pdfError, setPdfError] = useState("");
  const inspected = report.inspection?.files_inspected ?? 0;
  const found = report.summary?.skills_with_evidence ?? 0;
  const repositoryLink = safeGitHubUrl(report.repository.url);
  const outcomeCounts = report.skills.reduce(
    (counts, skill) => {
      if (Object.hasOwn(counts, skill.status)) {
        counts[skill.status] += 1;
      }
      return counts;
    },
    Object.fromEntries(CHART_STATUSES.map(({ id }) => [id, 0])),
  );
  const outcomeTotal = report.skills.length;
  const fileCounts = {
    considered: report.inspection?.files_considered ?? 0,
    selected: report.inspection?.files_selected ?? 0,
    inspected,
    skipped: report.inspection?.files_skipped ?? 0,
  };
  const selectedFileRatio = fileCounts.selected
    ? Math.min(fileCounts.inspected / fileCounts.selected, 1)
    : 0;
  const maxEvidenceCount = Math.max(
    1,
    ...report.skills.map((skill) => skill.evidence?.length ?? 0),
  );
  const evidenceDirectories = [...new Set(
    report.skills.flatMap((skill) =>
      (skill.evidence || [])
        .map((evidence) => evidence.file_path)
        .filter((filePath) => typeof filePath === "string" && filePath.length > 0),
    ),
  )].reduce((directories, filePath) => {
    const normalizedPath = filePath.replaceAll("\\", "/");
    const directory = normalizedPath.includes("/")
      ? normalizedPath.slice(0, normalizedPath.lastIndexOf("/"))
      : "(repository root)";
    directories.set(directory, (directories.get(directory) || 0) + 1);
    return directories;
  }, new Map());
  const directoryRows = [...evidenceDirectories.entries()]
    .sort(([directoryA], [directoryB]) => directoryA.localeCompare(directoryB));
  const maxDirectoryFiles = Math.max(
    1,
    ...directoryRows.map(([, count]) => count),
  );

  async function handleDownloadPdf() {
    setPdfError("");
    setIsPdfLoading(true);
    try {
      const { downloadReportPdf } = await import("./reportPdf.js");
      downloadReportPdf(report, { isDemo });
    } catch (error) {
      setPdfError(
        error instanceof Error
          ? `Could not create the PDF report: ${error.message}`
          : "Could not create the PDF report. Please try again.",
      );
    } finally {
      setIsPdfLoading(false);
    }
  }

  return (
    <div className="report-panel">
      <div className="report-header">
        <div>
          <p className="eyebrow">REPOSITORY EVIDENCE REPORT</p>
          <h2>{report.repository.full_name}</h2>
          {report.repository.description && (
            <p className="report-description">{report.repository.description}</p>
          )}
        </div>
        <div className="report-actions">
          <button className="button button-pdf" type="button" onClick={handleDownloadPdf} disabled={isPdfLoading}>
            {isPdfLoading ? <span className="spinner spinner-light" /> : <Icon name="download" size={16} />}
            {isPdfLoading ? "Preparing PDF…" : "Download PDF"}
          </button>
          <button className="button button-outline" type="button" onClick={onStartOver}>
            New analysis
          </button>
        </div>
      </div>

      {pdfError && <p className="form-error pdf-error" role="alert">{pdfError}</p>}

      {isDemo && (
        <div className="demo-banner" role="status">
          <Icon name="spark" size={17} />
          <span><strong>Illustrative sample.</strong> This fixture is not a live repository analysis.</span>
        </div>
      )}

      <div className="report-metrics" aria-label="Inspection summary">
        <div><span className="metric-value">{inspected}</span><span className="metric-label">files inspected</span></div>
        <div><span className="metric-value">{report.summary.selected_skills}</span><span className="metric-label">skills selected</span></div>
        <div><span className="metric-value">{found}</span><span className="metric-label">with evidence</span></div>
        {report.repository.primary_language && (
          <div><span className="metric-value metric-language">{report.repository.primary_language}</span><span className="metric-label">primary language</span></div>
        )}
      </div>

      {report.inspection?.limited_by_file_budget && (
        <p className="coverage-note">The file inspection limit was reached. Some repository files were not checked.</p>
      )}
      {report.inspection?.limited_by_time_budget && (
        <p className="coverage-note">The inspection time limit was reached. Some repository files were not checked.</p>
      )}

      <section className="dashboard" aria-labelledby="dashboard-title">
        <div className="dashboard-heading">
          <div>
            <p className="eyebrow">SCAN DASHBOARD</p>
            <h3 id="dashboard-title">Repository overview</h3>
          </div>
          <span>Bounded scan · {fileCounts.considered} repository files considered</span>
        </div>
        <div className="dashboard-grid">
          <section className="dashboard-card scan-card" aria-labelledby="scan-scope-title">
            <div className="dashboard-card-heading">
              <div>
                <span className="chart-kicker">FILE INSPECTION</span>
                <h4 id="scan-scope-title">Scan scope</h4>
              </div>
              <span className="scan-count">{fileCounts.considered}<small> files</small></span>
            </div>
            <div className="inspection-progress">
              <div
                className="inspection-ring"
                role="img"
                aria-label={`${fileCounts.inspected} of ${fileCounts.selected} selected files inspected`}
                style={{ "--inspection-progress": `${selectedFileRatio * 100}%` }}
              >
                <span>{fileCounts.selected ? `${Math.round(selectedFileRatio * 100)}%` : "—"}</span>
              </div>
              <p>of selected files<br />successfully inspected</p>
            </div>
            <div className="scope-rows">
              {[
                ["Considered in repository", fileCounts.considered, "scope-considered"],
                ["Selected for inspection", fileCounts.selected, "scope-selected"],
                ["Contents inspected", fileCounts.inspected, "scope-inspected"],
                ["Skipped / unavailable", fileCounts.skipped, "scope-skipped"],
              ].map(([label, count, className]) => (
                <div className="scope-row" key={label}>
                  <span>{label}</span>
                  <div className="scope-track" aria-hidden="true">
                    <span
                      className={className}
                      style={{
                        width: fileCounts.considered
                          ? `${Math.min((count / fileCounts.considered) * 100, 100)}%`
                          : "0%",
                      }}
                    />
                  </div>
                  <strong>{count}</strong>
                </div>
              ))}
            </div>
            <p className="chart-footnote">
              Only selected text files are inspected; this is not a full review of every repository file.
            </p>
          </section>

          <section className="dashboard-card outcomes-card" aria-labelledby="outcome-chart-title">
            <div className="dashboard-card-heading">
              <div>
                <span className="chart-kicker">SKILL RESULTS</span>
                <h4 id="outcome-chart-title">Selected skill outcomes</h4>
              </div>
              <span className="scan-count">{outcomeTotal}<small> selected</small></span>
            </div>
            <div
              className="outcome-bar"
              role="img"
              aria-label={`Outcomes across ${outcomeTotal} selected skills: ${CHART_STATUSES.map(({ id, label }) => `${outcomeCounts[id]} ${label.toLowerCase()}`).join(", ")}.`}
            >
              {CHART_STATUSES.map(({ id, label }) =>
                outcomeCounts[id] > 0 ? (
                  <span
                    className={`outcome-segment outcome-${id}`}
                    key={id}
                    style={{ width: `${(outcomeCounts[id] / outcomeTotal) * 100}%` }}
                    aria-hidden="true"
                    title={`${outcomeCounts[id]} ${label}`}
                  />
                ) : null,
              )}
            </div>
            <ul className="outcome-legend" aria-label="Outcome counts">
              {CHART_STATUSES.map(({ id, label }) => (
                <li key={id}>
                  <span className={`legend-dot outcome-${id}`} aria-hidden="true" />
                  <span>{label}</span>
                  <strong>{outcomeCounts[id]}</strong>
                </li>
              ))}
            </ul>
            <div className="evidence-volume" aria-label="Linked evidence records by selected skill">
              <div className="volume-heading">
                <span>Linked evidence records by skill</span>
                <span>records</span>
              </div>
              {report.skills.map((skill) => {
                const evidenceCount = skill.evidence?.length ?? 0;
                return (
                  <div className="volume-row" key={skill.id}>
                    <span className="volume-skill">{skill.name}</span>
                    <div className="volume-track" aria-hidden="true">
                      <span
                        className={`volume-fill outcome-${skill.status}`}
                        style={{
                          width: evidenceCount
                            ? `${(evidenceCount / maxEvidenceCount) * 100}%`
                            : "0%",
                        }}
                      />
                    </div>
                    <strong>{evidenceCount}</strong>
                  </div>
                );
              })}
            </div>
            <p className="chart-footnote">
              Outcomes are report findings—not skill scores or a measure of ability.
            </p>
          </section>

          <section className="dashboard-card folders-card" aria-labelledby="folder-chart-title">
            <div className="dashboard-card-heading">
              <div>
                <span className="chart-kicker">SOURCE LOCATIONS</span>
                <h4 id="folder-chart-title">Where linked evidence lives</h4>
              </div>
              <span className="scan-count">{directoryRows.reduce((sum, [, count]) => sum + count, 0)}<small> files</small></span>
            </div>
            {directoryRows.length ? (
              <div className="directory-chart" aria-label="Linked evidence files by directory">
                {directoryRows.map(([directory, count]) => (
                  <div className="directory-row" key={directory}>
                    <span title={directory}>{directory}</span>
                    <div className="directory-track" aria-hidden="true">
                      <span style={{ width: `${(count / maxDirectoryFiles) * 100}%` }} />
                    </div>
                    <strong>{count}</strong>
                  </div>
                ))}
              </div>
            ) : (
              <p className="empty-chart">
                No source files were linked for the selected skills in this report.
              </p>
            )}
            <p className="chart-footnote">
              Counts use unique source paths linked to selected-skill findings only; other scanned files may not appear here.
            </p>
          </section>
        </div>
      </section>

      <div className="results-heading">
        <div>
          <p className="eyebrow">THE FINDINGS</p>
          <h3>Evidence to explore</h3>
        </div>
        {repositoryLink && (
          <a
            className="repository-link"
            href={repositoryLink}
            target="_blank"
            rel="noreferrer"
          >
            View repository <Icon name="external" size={15} />
          </a>
        )}
      </div>

      <div className="result-list">
        {report.skills.map((skill) => (
          <article className="result-card" key={skill.id}>
            <div className="result-topline">
              <div>
                <span className="result-category">{skill.category}</span>
                <h4>{skill.name}</h4>
              </div>
              <span className={`status-badge status-${skill.status}`}>
                <span className="badge-dot" />
                {STATUS_LABELS[skill.status] || skill.status.replaceAll("_", " ")}
              </span>
            </div>
            <p className="result-explanation">{skill.explanation}</p>
            {skill.evidence?.length > 0 && (
              <ul className="evidence-list">
                {skill.evidence.map((evidence, index) => (
                  <li key={`${evidence.file_path}-${index}`}>
                    <span className="evidence-icon"><Icon name="check" size={14} /></span>
                    <div className="evidence-content">
                      {safeGitHubUrl(evidence.file_url) ? (
                        <a href={safeGitHubUrl(evidence.file_url)} target="_blank" rel="noreferrer">
                          {evidence.file_path} <Icon name="external" size={13} />
                        </a>
                      ) : (
                        <span className="evidence-path">{evidence.file_path}</span>
                      )}
                      <p>{evidence.description}</p>
                    </div>
                    <span className="evidence-type">{evidence.evidence_type.replaceAll("_", " ")}</span>
                  </li>
                ))}
              </ul>
            )}
            {skill.recommended_next_steps?.length > 0 && (
              <div className="next-step">
                <span>CONSIDER NEXT</span>
                <p>{skill.recommended_next_steps[0]}</p>
              </div>
            )}
          </article>
        ))}
      </div>

      <div className="limitations-panel">
        <div className="limitations-heading">
          <Icon name="shield" size={18} />
          <h3>Read this report with care</h3>
        </div>
        <p>
          Static inspection cannot establish authorship, proficiency, or code
          quality. Not found is not a negative judgement. Use this report to
          guide a human review, walkthrough, or relevant practical task.
        </p>
        <ul>
          {report.limitations?.map((limitation) => (
            <li key={limitation}>{limitation}</li>
          ))}
        </ul>
      </div>
    </div>
  );
}

export default App;
