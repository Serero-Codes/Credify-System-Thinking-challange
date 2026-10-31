import { jsPDF } from "jspdf";

const COLORS = {
  ink: [23, 42, 43],
  muted: [104, 119, 111],
  teal: [19, 126, 114],
  line: [225, 233, 226],
  evidence_found: [34, 130, 97],
  needs_further_assessment: [223, 185, 78],
  not_found_in_inspected_files: [175, 183, 171],
  inspection_incomplete: [201, 122, 95],
};

const STATUS_LABELS = {
  evidence_found: "Evidence found",
  not_found_in_inspected_files: "Not found in inspected files",
  needs_further_assessment: "Needs further assessment",
  inspection_incomplete: "Inspection incomplete",
};

const PAGE = {
  width: 210,
  height: 297,
  margin: 18,
  contentWidth: 174,
};

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

function safeFilename(value) {
  return (value || "skillproof-report")
    .replace(/[^a-z0-9._-]+/gi, "-")
    .replace(/^-+|-+$/g, "")
    .toLowerCase() || "skillproof-report";
}

export function createReportPdf(report, { isDemo = false } = {}) {
  const doc = new jsPDF({ format: "a4", unit: "mm" });
  const skills = Array.isArray(report.skills) ? report.skills : [];
  const repository = report.repository || {};
  const inspection = report.inspection || {};
  const summary = report.summary || {};
  const outcomeCounts = skills.reduce(
    (counts, skill) => {
      if (Object.hasOwn(counts, skill.status)) {
        counts[skill.status] += 1;
      }
      return counts;
    },
    {
      evidence_found: 0,
      needs_further_assessment: 0,
      not_found_in_inspected_files: 0,
      inspection_incomplete: 0,
    },
  );
  let y = PAGE.margin;

  doc.setProperties({
    title: `SkillProof evidence report - ${repository.full_name || repository.name || "repository"}`,
    subject: "Source-linked repository evidence for human review",
    author: "SkillProof",
    creator: "SkillProof",
  });

  function ensureSpace(height) {
    if (y + height > PAGE.height - PAGE.margin) {
      doc.addPage();
      y = PAGE.margin;
    }
  }

  function addText(text, {
    size = 9,
    color = COLORS.ink,
    bold = false,
    indent = 0,
    link,
    gapAfter = 2,
  } = {}) {
    if (text === null || text === undefined || text === "") return;
    const lines = doc.splitTextToSize(
      String(text),
      PAGE.contentWidth - indent,
    );
    const lineHeight = size * 0.48;
    ensureSpace(lines.length * lineHeight + gapAfter);
    doc.setFont("helvetica", bold ? "bold" : "normal");
    doc.setFontSize(size);
    doc.setTextColor(...color);
    if (link) {
      doc.text(lines, PAGE.margin + indent, y, { url: link });
    } else {
      doc.text(lines, PAGE.margin + indent, y);
    }
    y += lines.length * lineHeight + gapAfter;
  }

  function addSection(title) {
    ensureSpace(13);
    y += 3;
    doc.setDrawColor(...COLORS.line);
    doc.line(PAGE.margin, y, PAGE.width - PAGE.margin, y);
    y += 7;
    addText(title.toUpperCase(), {
      size: 9,
      color: COLORS.teal,
      bold: true,
      gapAfter: 3,
    });
  }

  function addField(label, value, options = {}) {
    if (value === null || value === undefined || value === "") return;
    addText(label, { size: 8, color: COLORS.muted, bold: true, gapAfter: 1 });
    addText(value, { size: 9, ...options, gapAfter: 3 });
  }

  function addList(items) {
    for (const item of items || []) {
      addText(`- ${item}`, { size: 8.5, indent: 2, gapAfter: 2 });
    }
  }

  function addBarRow(label, value, maximum, color) {
    ensureSpace(9);
    doc.setFont("helvetica", "normal");
    doc.setFontSize(7.5);
    doc.setTextColor(...COLORS.muted);
    doc.text(doc.splitTextToSize(String(label), 118)[0] || "", PAGE.margin, y);
    doc.setFont("helvetica", "bold");
    doc.setTextColor(...COLORS.ink);
    doc.text(String(value), PAGE.width - PAGE.margin, y, { align: "right" });

    const barX = PAGE.margin;
    const barY = y + 2;
    const barWidth = PAGE.contentWidth;
    doc.setFillColor(237, 241, 237);
    doc.roundedRect(barX, barY, barWidth, 2.5, 1, 1, "F");
    if (value > 0 && maximum > 0) {
      doc.setFillColor(...color);
      doc.roundedRect(
        barX,
        barY,
        Math.max(1, barWidth * Math.min(value / maximum, 1)),
        2.5,
        1,
        1,
        "F",
      );
    }
    y += 8;
  }

  function addFooter() {
    const pageCount = doc.getNumberOfPages();
    for (let page = 1; page <= pageCount; page += 1) {
      doc.setPage(page);
      doc.setDrawColor(...COLORS.line);
      doc.line(PAGE.margin, PAGE.height - 13, PAGE.width - PAGE.margin, PAGE.height - 13);
      doc.setFont("helvetica", "normal");
      doc.setFontSize(7);
      doc.setTextColor(...COLORS.muted);
      doc.text("SkillProof | Evidence for human review, not a hiring decision", PAGE.margin, PAGE.height - 8);
      doc.text(`${page} / ${pageCount}`, PAGE.width - PAGE.margin, PAGE.height - 8, { align: "right" });
    }
  }

  doc.setFillColor(...COLORS.teal);
  doc.roundedRect(PAGE.margin, y - 2, 8, 8, 1.5, 1.5, "F");
  doc.setFont("helvetica", "bold");
  doc.setFontSize(10);
  doc.setTextColor(255, 255, 255);
  doc.text("S", PAGE.margin + 2.7, y + 3.8);
  doc.setFontSize(17);
  doc.setTextColor(...COLORS.ink);
  doc.text("SkillProof evidence report", PAGE.margin + 12, y + 4);
  y += 12;

  if (isDemo) {
    doc.setFillColor(243, 247, 233);
    doc.roundedRect(PAGE.margin, y - 3, PAGE.contentWidth, 10, 1, 1, "F");
    addText("ILLUSTRATIVE SAMPLE - This fixture is not a live repository analysis.", {
      size: 8,
      color: COLORS.muted,
      bold: true,
      indent: 3,
      gapAfter: 4,
    });
  }

  addText(repository.full_name || repository.name || "Repository", {
    size: 15,
    bold: true,
    gapAfter: 2,
  });
  if (repository.description) {
    addText(repository.description, { size: 9, color: COLORS.muted, gapAfter: 3 });
  }
  const repositoryUrl = safeGitHubUrl(repository.url);
  if (repositoryUrl) {
    addText(repositoryUrl, { size: 8, color: COLORS.teal, link: repositoryUrl, gapAfter: 4 });
  }
  addText(
    `Report generated: ${report.analysed_at || new Date().toISOString()}`,
    { size: 8, color: COLORS.muted, gapAfter: 3 },
  );

  addSection("Repository details");
  addField("Repository", repository.full_name || repository.name);
  addField("Owner", repository.owner);
  addField("Description", repository.description);
  addField("Repository URL", repository.url, {
    size: 8.5,
    color: COLORS.teal,
    link: repositoryUrl,
  });
  addField("Primary language", repository.primary_language);
  addField("Default branch", repository.default_branch);

  addSection("Inspection coverage");
  addField(
    "Files",
    `${inspection.files_inspected ?? 0} inspected / ${inspection.files_selected ?? 0} selected / ${inspection.files_considered ?? 0} considered`,
  );
  addField("Files skipped", inspection.files_skipped ?? 0);
  addField(
    "File limit reached",
    inspection.limited_by_file_budget ? "Yes - some files may not have been inspected." : "No",
  );
  addField(
    "Time limit reached",
    inspection.limited_by_time_budget ? "Yes - some files may not have been inspected." : "No",
  );
  const maxFileCount = Math.max(
    1,
    inspection.files_considered || 0,
    inspection.files_selected || 0,
    inspection.files_inspected || 0,
  );
  addBarRow("Files considered in repository", inspection.files_considered || 0, maxFileCount, [156, 172, 160]);
  addBarRow("Files selected for inspection", inspection.files_selected || 0, maxFileCount, [110, 168, 151]);
  addBarRow("File contents inspected", inspection.files_inspected || 0, maxFileCount, COLORS.teal);
  addBarRow("Selected files skipped / unavailable", inspection.files_skipped || 0, maxFileCount, [201, 122, 95]);
  addText(
    "Counts show bounded inspection stages, not exhaustive analysis of every repository file.",
    { size: 7.5, color: COLORS.muted, gapAfter: 2 },
  );

  addSection("Skills selected and outcome summary");
  addField(
    "Summary",
    `${summary.selected_skills ?? skills.length} selected | ${summary.skills_with_evidence ?? outcomeCounts.evidence_found} with evidence | ${summary.skills_needing_further_assessment ?? (skills.length - outcomeCounts.evidence_found)} needing further assessment`,
  );

  const chartX = PAGE.margin;
  const chartHeight = 7;
  const chartWidth = PAGE.contentWidth;
  ensureSpace(chartHeight + 20);
  const chartY = y;
  doc.setFillColor(237, 241, 237);
  doc.roundedRect(chartX, chartY, chartWidth, chartHeight, 1, 1, "F");
  const total = skills.length;
  if (total > 0) {
    let segmentX = chartX;
    for (const status of [
      "evidence_found",
      "needs_further_assessment",
      "not_found_in_inspected_files",
      "inspection_incomplete",
    ]) {
      const count = outcomeCounts[status];
      if (count === 0) continue;
      const segmentWidth = chartWidth * (count / total);
      doc.setFillColor(...COLORS[status]);
      doc.rect(segmentX, chartY, segmentWidth, chartHeight, "F");
      segmentX += segmentWidth;
    }
  }
  y += chartHeight + 4;

  for (const [status, label] of [
    ["evidence_found", "Evidence found"],
    ["needs_further_assessment", "Needs further assessment"],
    ["not_found_in_inspected_files", "Not found in inspected files"],
    ["inspection_incomplete", "Inspection incomplete"],
  ]) {
    doc.setFillColor(...COLORS[status]);
    doc.rect(PAGE.margin, y - 2.4, 3, 3, "F");
    addText(`${label}: ${outcomeCounts[status]}`, {
      size: 8,
      indent: 5,
      gapAfter: 1,
    });
  }
  addText(
    "These counts describe report findings only. They are not skill scores or a measure of a person's ability.",
    { size: 8, color: COLORS.muted, gapAfter: 3 },
  );

  addSection("Linked evidence distribution");
  addText("Evidence records by selected skill", {
    size: 8,
    color: COLORS.muted,
    bold: true,
    gapAfter: 2,
  });
  const maxSkillEvidence = Math.max(
    1,
    ...skills.map((skill) => skill.evidence?.length ?? 0),
  );
  for (const skill of skills) {
    addBarRow(
      skill.name || skill.id || "Skill",
      skill.evidence?.length ?? 0,
      maxSkillEvidence,
      COLORS[skill.status] || COLORS.teal,
    );
  }
  const evidenceDirectories = [...new Set(
    skills.flatMap((skill) =>
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
  if (evidenceDirectories.size) {
    addText("Unique linked source files by directory", {
      size: 8,
      color: COLORS.muted,
      bold: true,
      gapAfter: 2,
    });
    const maxDirectoryFiles = Math.max(1, ...evidenceDirectories.values());
    for (const [directory, count] of [...evidenceDirectories.entries()].sort(
      ([directoryA], [directoryB]) => directoryA.localeCompare(directoryB),
    )) {
      addBarRow(directory, count, maxDirectoryFiles, COLORS.teal);
    }
  } else {
    addText("No source files were linked for the selected skills.", {
      size: 8,
      color: COLORS.muted,
    });
  }
  addText(
    "Evidence and directory visuals include linked files for selected-skill findings only; they are not a complete repository file inventory.",
    { size: 7.5, color: COLORS.muted, gapAfter: 3 },
  );

  addSection("Analysis results");
  if (skills.length === 0) {
    addText("No skill results were included in this report.", {
      size: 9,
      color: COLORS.muted,
    });
  }
  for (const skill of skills) {
    ensureSpace(17);
    y += 2;
    addText(skill.name || skill.id || "Skill", { size: 11, bold: true, gapAfter: 1 });
    addText(
      `${skill.category || "Uncategorised"} | ${STATUS_LABELS[skill.status] || skill.status || "Status unavailable"}`,
      { size: 8, color: COLORS.teal, bold: true, gapAfter: 2 },
    );
    addField("Analysis", skill.explanation);

    if (skill.evidence?.length) {
      addText("Evidence identified", { size: 8, color: COLORS.muted, bold: true, gapAfter: 1 });
      for (const evidence of skill.evidence) {
        const sourceUrl = safeGitHubUrl(evidence.file_url);
        addText(
          `${evidence.file_path || "Source file"}${evidence.evidence_type ? ` | ${evidence.evidence_type.replaceAll("_", " ")}` : ""}`,
          { size: 8.5, bold: true, indent: 3, gapAfter: 1 },
        );
        if (sourceUrl) {
          addText(sourceUrl, { size: 7.5, color: COLORS.teal, indent: 3, link: sourceUrl, gapAfter: 1 });
        }
        addText(evidence.description, { size: 8, indent: 3, gapAfter: 1 });
        if (evidence.limitations) {
          addText(`Evidence limitation: ${evidence.limitations}`, {
            size: 7.5,
            color: COLORS.muted,
            indent: 3,
            gapAfter: 2,
          });
        }
      }
    } else {
      addText("No source evidence was linked for this result.", {
        size: 8,
        color: COLORS.muted,
        indent: 3,
        gapAfter: 2,
      });
    }

    if (skill.recommended_next_steps?.length) {
      addText("Recommended next steps", {
        size: 8,
        color: COLORS.muted,
        bold: true,
        gapAfter: 1,
      });
      addList(skill.recommended_next_steps);
    }
    if (skill.limitations?.length) {
      addText("Skill-specific limitations", {
        size: 8,
        color: COLORS.muted,
        bold: true,
        gapAfter: 1,
      });
      addList(skill.limitations);
    }
    y += 2;
  }

  addSection("Report analysis and limitations");
  addText(
    "This report identifies predefined patterns in a bounded set of accessible public repository files. A finding is a lead for human review, not proof of authorship, proficiency, code quality, or production readiness. Not found in inspected files does not mean the person lacks the skill. Inspection that is incomplete must not be interpreted as a negative finding. Use a project walkthrough or relevant practical task for further assessment. This report does not rank candidates, certify skills, or make hiring decisions.",
    { size: 8.5, gapAfter: 4 },
  );
  addList(report.limitations);

  addFooter();
  return doc;
}

export function downloadReportPdf(report, options) {
  const doc = createReportPdf(report, options);
  const repositoryName =
    report.repository?.full_name || report.repository?.name || "skillproof-report";
  doc.save(`${safeFilename(repositoryName)}-evidence-report.pdf`);
}
