const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim();
const apiBaseUrl = configuredBaseUrl
  ? configuredBaseUrl.replace(/\/+$/, "")
  : "";

async function request(path, options) {
  let response;
  try {
    response = await fetch(`${apiBaseUrl}${path}`, options);
  } catch {
    throw new Error("Could not reach SkillProof. Check that the backend is running.");
  }

  let data;
  try {
    data = await response.json();
  } catch {
    data = null;
  }

  if (!response.ok) {
    throw new Error(
      data?.error?.message || `SkillProof returned an error (${response.status}).`,
    );
  }

  return data;
}

export function getHealth() {
  return request("/api/health");
}

export function getSkills() {
  return request("/api/skills");
}

export function analyzeRepository(repositoryUrl, skills) {
  return request("/api/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      repository_url: repositoryUrl,
      skills,
    }),
  });
}
