"use client";

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";

interface UploadedFile {
  id: string;
  original_name: string;
  file_type: string;
  uploaded_at: string;
}

interface ReportJob {
  id: string;
  event_name: string;
  status: "pending" | "processing" | "completed" | "failed";
  created_at: string;
  completed_at: string | null;
  output_file: string | null;
  error: string | null;
}

export default function ReportsPage() {
  const [uploads, setUploads] = useState<UploadedFile[]>([]);
  const [jobs, setJobs] = useState<ReportJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [generating, setGenerating] = useState(false);

  // Form state
  const [eventName, setEventName] = useState("");
  const [eventDate, setEventDate] = useState("");
  const [transcriptId, setTranscriptId] = useState("");
  const [surveyId, setSurveyId] = useState("");

  const loadData = useCallback(async () => {
    try {
      const [uploadsRes, jobsRes] = await Promise.all([
        api.get("/reports/uploads"),
        api.get("/reports/jobs"),
      ]);
      setUploads(uploadsRes.data);
      setJobs(jobsRes.data);
    } catch (error) {
      console.error("Failed to load reports data:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>, fileType: "transcript" | "survey") => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("file_type", fileType);

      await api.post("/reports/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      await loadData();
    } catch (error) {
      console.error("Upload failed:", error);
      alert("Upload failed. Please check file type.");
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!eventName || !eventDate || !transcriptId || !surveyId) {
      alert("Please fill all fields");
      return;
    }

    setGenerating(true);
    try {
      await api.post("/reports/generate", {
        event_name: eventName,
        event_date: eventDate,
        transcript_file_id: transcriptId,
        survey_file_id: surveyId,
      });

      setEventName("");
      setEventDate("");
      setTranscriptId("");
      setSurveyId("");
      await loadData();
    } catch (error) {
      console.error("Generation failed:", error);
      alert("Failed to start report generation");
    } finally {
      setGenerating(false);
    }
  };

  const handleDownload = async (jobId: string, eventName: string) => {
    try {
      const response = await api.get(`/reports/jobs/${jobId}/download`, {
        responseType: "blob",
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `${eventName}_report.pptx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error("Download failed:", error);
      alert("Failed to download report");
    }
  };

  const transcriptFiles = uploads.filter((f) => f.file_type === "transcript");
  const surveyFiles = uploads.filter((f) => f.file_type === "survey");

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Reports</h1>
        <p className="text-gray-600 mt-1">
          Generate presentation reports from event transcripts and survey data.
        </p>
      </div>

      {/* Upload Section */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">Upload Files</h2>
        <div className="grid md:grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Transcript (.txt, .vtt, .srt, .docx)
            </label>
            <input
              type="file"
              accept=".txt,.vtt,.srt,.docx"
              onChange={(e) => handleUpload(e, "transcript")}
              disabled={uploading}
              className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 disabled:opacity-50"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Survey (.csv, .xlsx, .xls)
            </label>
            <input
              type="file"
              accept=".csv,.xlsx,.xls"
              onChange={(e) => handleUpload(e, "survey")}
              disabled={uploading}
              className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-medium file:bg-green-50 file:text-green-700 hover:file:bg-green-100 disabled:opacity-50"
            />
          </div>
        </div>
      </div>

      {/* Generate Form */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">Generate Report</h2>
        <form onSubmit={handleGenerate} className="space-y-4">
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Event Name
              </label>
              <input
                type="text"
                value={eventName}
                onChange={(e) => setEventName(e.target.value)}
                placeholder="Q1 Medical Conference"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Event Date
              </label>
              <input
                type="date"
                value={eventDate}
                onChange={(e) => setEventDate(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Transcript File
              </label>
              <select
                value={transcriptId}
                onChange={(e) => setTranscriptId(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Select transcript...</option>
                {transcriptFiles.map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.original_name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Survey File
              </label>
              <select
                value={surveyId}
                onChange={(e) => setSurveyId(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Select survey...</option>
                {surveyFiles.map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.original_name}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <button
            type="submit"
            disabled={generating || !eventName || !eventDate || !transcriptId || !surveyId}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {generating ? "Starting..." : "Generate Report"}
          </button>
        </form>
      </div>

      {/* Jobs List */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">Report Jobs</h2>
        {jobs.length === 0 ? (
          <p className="text-gray-500">No report jobs yet.</p>
        ) : (
          <div className="space-y-4">
            {jobs.map((job) => (
              <div
                key={job.id}
                className="flex items-center justify-between p-4 border rounded-lg"
              >
                <div>
                  <p className="font-medium">{job.event_name}</p>
                  <p className="text-sm text-gray-500">
                    {new Date(job.created_at).toLocaleString()}
                  </p>
                </div>
                <div className="flex items-center gap-4">
                  <span
                    className={`px-2 py-1 text-xs rounded-full ${
                      job.status === "completed"
                        ? "bg-green-100 text-green-800"
                        : job.status === "failed"
                        ? "bg-red-100 text-red-800"
                        : job.status === "processing"
                        ? "bg-yellow-100 text-yellow-800"
                        : "bg-gray-100 text-gray-800"
                    }`}
                  >
                    {job.status}
                  </span>
                  {job.status === "completed" && (
                    <button
                      onClick={() => handleDownload(job.id, job.event_name)}
                      className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
                    >
                      Download
                    </button>
                  )}
                  {job.status === "failed" && job.error && (
                    <span className="text-xs text-red-600 max-w-xs truncate">
                      {job.error}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
