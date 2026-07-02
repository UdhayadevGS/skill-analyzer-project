import { useMemo, useRef, useState } from "react";
import "./App.css";

const JOBS = [
  "Automation Engineer",
  "Frontend Developer",
  "Backend Developer",
  "Full Stack Developer",
  "DevOps Engineer",
  "Cloud Engineer",
  "Data Analyst",
  "Data Scientist",
  "Machine Learning Engineer",
  "AI Engineer",
  "Cybersecurity Analyst",
  "QA Engineer",
  "Mobile App Developer",
  "UI/UX Designer",
  "Database Administrator",
  "Software Engineer",
];

const steps = [
  "Uploading files",
  "Reading resume and certificates",
  "Checking GitHub links",
  "Scoring selected jobs",
];

async function readJson(response) {
  const text = await response.text();
  if (!text.trim()) throw new Error("Backend returned an empty response.");

  try {
    return JSON.parse(text);
  } catch {
    throw new Error(`Backend returned invalid JSON: ${text.slice(0, 160)}`);
  }
}

function scoreValue(score) {
  const value = Number(score);
  return Number.isFinite(value) ? Math.max(0, Math.min(100, Math.round(value))) : null;
}

export default function App() {
  const certInputRef = useRef(null);
  const [jobText, setJobText] = useState("");
  const [jobs, setJobs] = useState([]);
  const [showJobs, setShowJobs] = useState(false);
  const [resume, setResume] = useState(null);
  const [certificates, setCertificates] = useState([]);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  const jobMatches = useMemo(() => {
    const query = jobText.trim().toLowerCase();
    return JOBS.filter((job) => !jobs.includes(job) && job.toLowerCase().includes(query)).slice(0, 8);
  }, [jobText, jobs]);

  function addJob(job) {
    setJobs([...jobs, job]);
    setJobText("");
    setShowJobs(false);
  }

  function addCertificates(fileList) {
    setCertificates([...certificates, ...Array.from(fileList)]);
    if (certInputRef.current) certInputRef.current.value = "";
  }

  function removeCertificate(fileToRemove) {
    setCertificates(
      certificates.filter(
        (file) =>
          file.name !== fileToRemove.name ||
          file.size !== fileToRemove.size ||
          file.lastModified !== fileToRemove.lastModified
      )
    );
  }

  async function analyzeProfile(event) {
    event.preventDefault();
    setError("");
    setResult(null);

    if (!jobs.length) {
      setError("Choose at least one job preference.");
      return;
    }

    const formData = new FormData();
    formData.append("job_preferences", jobs.join(", "));
    if (resume) formData.append("resume_file", resume);
    certificates.forEach((file) => formData.append("certificate_files", file));

    setLoading(true);
    setProgress(10);
    const timer = window.setInterval(() => setProgress((value) => Math.min(value + 10, 90)), 700);

    try {
      const response = await fetch("/api/analyze-profile", { method: "POST", body: formData });
      const data = await readJson(response);
      if (!response.ok) throw new Error(data.detail || "Failed to analyze profile.");
      setProgress(100);
      setResult(data);
    } catch (err) {
      setError(err.message === "Failed to fetch" ? "Backend is not running on port 8000." : err.message);
    } finally {
      window.clearInterval(timer);
      setLoading(false);
    }
  }

  const stepText = steps[Math.min(steps.length - 1, Math.floor((progress / 100) * steps.length))];

  return (
    <main className="page">
      <section className="panel">
        <h1>AI Skill Analyzer Dashboard</h1>

        <form onSubmit={analyzeProfile} className="form">
          <label>
            Job Preferences
            <input
              value={jobText}
              onChange={(event) => setJobText(event.target.value)}
              onFocus={() => setShowJobs(true)}
              placeholder="Type a role, then choose one"
            />
          </label>

          {showJobs && jobMatches.length > 0 && (
            <div className="dropdown">
              {jobMatches.map((job) => (
                <button type="button" key={job} onMouseDown={() => addJob(job)}>
                  {job}
                </button>
              ))}
            </div>
          )}

          {jobs.length > 0 && (
            <div className="chips">
              {jobs.map((job) => (
                <span key={job}>
                  {job}
                  <button type="button" onClick={() => setJobs(jobs.filter((item) => item !== job))}>
                    x
                  </button>
                </span>
              ))}
            </div>
          )}

          <label>
            Resume (PDF)
            <input type="file" accept=".pdf" onChange={(event) => setResume(event.target.files[0] || null)} />
          </label>

          <label>
            Certificates (PDFs)
            <input
              ref={certInputRef}
              type="file"
              accept=".pdf"
              multiple
              onChange={(event) => addCertificates(event.target.files)}
            />
          </label>

          {certificates.length > 0 && (
            <ul className="files">
              {certificates.map((file) => (
                <li key={`${file.name}-${file.size}-${file.lastModified}`}>
                  <span>{file.name}</span>
                  <button type="button" onClick={() => removeCertificate(file)}>
                    Remove
                  </button>
                </li>
              ))}
            </ul>
          )}

          <button className="primary" disabled={loading}>
            {loading ? "Analyzing..." : "Analyze Profile"}
          </button>
        </form>

        {loading && (
          <div className="loading">
            <div>
              <strong>{stepText}</strong>
              <span>{progress}%</span>
            </div>
            <progress value={progress} max="100" />
          </div>
        )}

        {error && <div className="error">Error: {error}</div>}

        {result && (
          <section className="results">
            <h2>Analysis Results</h2>
            {result.summary && <p>{result.summary}</p>}

            {result.role_scores?.map((item) => {
              const score = scoreValue(item.score);
              return (
                <article className="score-card" key={item.role}>
                  <header>
                    <h3>{item.role}</h3>
                    <strong>{score === null ? "N/A" : `${score}%`}</strong>
                  </header>
                  <progress value={score || 0} max="100" />
                  <p>{item.why}</p>
                  <p><b>Resume:</b> {item.resume_evidence}</p>
                  <p><b>Certificates:</b> {item.certification_evidence}</p>
                  <p><b>GitHub:</b> {item.github_evidence}</p>
                  <p><b>Improve:</b> {item.recommendation}</p>
                </article>
              );
            })}
          </section>
        )}
      </section>
    </main>
  );
}
