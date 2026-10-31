export const demoReport = {
  repository: {
    name: "example-project",
    owner: "example-user",
    full_name: "example-user/example-project",
    url: "https://github.com/example-user/example-project",
    description: "Illustrative fixture report for a product demonstration.",
    primary_language: "Python",
    default_branch: "main",
  },
  inspection: {
    files_considered: 18,
    files_selected: 8,
    files_inspected: 8,
    files_skipped: 0,
    limited_by_file_budget: false,
    limited_by_time_budget: false,
  },
  summary: {
    selected_skills: 3,
    skills_with_evidence: 1,
    skills_needing_further_assessment: 2,
  },
  skills: [
    {
      id: "python",
      name: "Python",
      category: "Programming",
      status: "evidence_found",
      explanation:
        "A recognised source pattern was found in an inspected file. This is a lead for human review, not proof of proficiency.",
      evidence: [
        {
          file_path: "src/app.py",
          file_url:
            "https://github.com/example-user/example-project/blob/main/src/app.py",
          evidence_type: "source_code",
          description: "Python source with function definitions.",
          limitations: "Code presence does not confirm authorship or independent proficiency.",
        },
      ],
      recommended_next_steps: [
        "Ask for a short walkthrough or a role-relevant practical task.",
      ],
      limitations: [
        "Static inspection cannot confirm authorship, code quality, or independent proficiency.",
      ],
    },
    {
      id: "rest_apis",
      name: "REST APIs",
      category: "Backend development",
      status: "needs_further_assessment",
      explanation:
        "The available evidence is insufficient to make a finding. A practical task or walkthrough can provide clearer evidence.",
      evidence: [],
      recommended_next_steps: [
        "Review an API implementation together or use a structured practical task.",
      ],
      limitations: [
        "This illustrative report does not establish API design ability.",
      ],
    },
    {
      id: "docker",
      name: "Docker",
      category: "Cloud and DevOps",
      status: "not_found_in_inspected_files",
      explanation:
        "No recognised evidence was found in the inspected files. This does not mean the person lacks the skill.",
      evidence: [],
      recommended_next_steps: [
        "Check another repository or use an accessible practical assessment.",
      ],
      limitations: [
        "Absence of evidence in inspected files is not evidence of absence of the skill.",
      ],
    },
  ],
  limitations: [
    "This is illustrative fixture data, not a live repository analysis.",
    "A bounded selection of accessible files is inspected.",
    "Evidence patterns can miss valid implementations and do not prove authorship or proficiency.",
    "The report supports human review; it does not rank or certify candidates.",
  ],
  analysed_at: "Illustrative sample",
};
