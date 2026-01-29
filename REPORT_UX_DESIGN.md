# Report Generation UX Design

## Goals
1. **Real-time feedback** - User sees exactly what's happening
2. **Progress visualization** - Clear indication of completion percentage
3. **Stage descriptions** - Human-readable status at each step
4. **Optional preview** - See content as it's generated (stretch goal)

---

## Report Generation Pipeline Stages

Based on the `chm_report_automation` pipeline, here are the stages:

| Stage | Description | % | Duration (est.) |
|-------|-------------|---|-----------------|
| 1. Upload Processing | Validating and parsing files | 0-5% | 2-5s |
| 2. Transcript Analysis | Extracting speakers and content | 5-15% | 5-10s |
| 3. Survey Processing | Parsing survey responses | 15-25% | 3-5s |
| 4. Executive Summary | AI generating summary | 25-35% | 15-30s |
| 5. Conversation Analysis | AI extracting key topics | 35-50% | 20-40s |
| 6. Key Takeaways | AI generating insights | 50-60% | 15-30s |
| 7. Quote Extraction | AI finding notable quotes | 60-70% | 15-25s |
| 8. Survey Insights | AI analyzing survey themes | 70-80% | 15-25s |
| 9. Chart Generation | Creating visualizations | 80-90% | 10-20s |
| 10. PPTX Assembly | Building final presentation | 90-100% | 5-10s |

**Total estimated time:** 2-4 minutes (OpenAI) or 8-15 minutes (Ollama/CPU)

---

## UI Design

### Progress Card Component

```
┌─────────────────────────────────────────────────────────────────┐
│  Generating Report: "HER2 Webinar - November 2025"              │
│                                                                 │
│  ████████████████████░░░░░░░░░░░░░░░░░░░░░░░░░  47%            │
│                                                                 │
│  ⚡ Generating Key Takeaways...                                 │
│     Analyzing clinical implications from webinar discussion     │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ ✓ Upload Processing              2s                       │ │
│  │ ✓ Transcript Analysis            8s                       │ │
│  │ ✓ Survey Processing              4s                       │ │
│  │ ✓ Executive Summary              18s                      │ │
│  │ ✓ Conversation Analysis          32s                      │ │
│  │ ● Key Takeaways                  12s...                   │ │
│  │ ○ Quote Extraction                                        │ │
│  │ ○ Survey Insights                                         │ │
│  │ ○ Chart Generation                                        │ │
│  │ ○ PPTX Assembly                                           │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  Elapsed: 1:16  │  Est. Remaining: ~1:30                       │
│                                                                 │
│  [Cancel]                                                       │
└─────────────────────────────────────────────────────────────────┘
```

### Key UI Elements

1. **Animated Progress Bar**
   - Smooth CSS animation
   - Gradient fill (CHM purple to cyan)
   - Percentage label

2. **Current Stage Indicator**
   - Lightning bolt icon (⚡) for active stage
   - Descriptive subtitle explaining what's happening
   - Pulsing animation

3. **Stage Checklist**
   - ✓ Completed (green)
   - ● In Progress (animated pulse, blue)
   - ○ Pending (gray)
   - Duration shown for completed stages

4. **Time Estimates**
   - Elapsed time (real)
   - Estimated remaining (calculated from stage averages)

5. **Cancel Button**
   - Allows user to abort long-running jobs

---

## Technical Implementation

### Backend: Server-Sent Events (SSE)

Use SSE for real-time progress updates (simpler than WebSockets).

```python
# backend/routers/reports.py

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import asyncio
import json

@router.get("/jobs/{job_id}/progress")
async def stream_progress(job_id: str):
    """Stream real-time progress updates via SSE."""

    async def event_generator():
        while True:
            job = get_job(job_id)
            if not job:
                break

            data = {
                "stage": job.current_stage,
                "stage_name": job.stage_name,
                "stage_description": job.stage_description,
                "progress": job.progress_percent,
                "elapsed_seconds": job.elapsed_seconds,
                "stages_completed": job.completed_stages,
                "status": job.status,
            }

            yield f"data: {json.dumps(data)}\n\n"

            if job.status in ("completed", "failed"):
                break

            await asyncio.sleep(0.5)  # 500ms refresh rate

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
```

### Pipeline Progress Callbacks

Modify pipeline to emit progress updates:

```python
# chm_report_automation/src/pipeline.py

class ProgressTracker:
    def __init__(self, callback):
        self.callback = callback
        self.stages = [
            ("upload", "Upload Processing", "Validating files"),
            ("transcript", "Transcript Analysis", "Extracting speakers"),
            ("survey", "Survey Processing", "Parsing responses"),
            ("executive", "Executive Summary", "AI generating summary"),
            ("conversation", "Conversation Analysis", "Extracting key topics"),
            ("takeaways", "Key Takeaways", "Generating insights"),
            ("quotes", "Quote Extraction", "Finding notable quotes"),
            ("survey_insights", "Survey Insights", "Analyzing themes"),
            ("charts", "Chart Generation", "Creating visualizations"),
            ("assembly", "PPTX Assembly", "Building presentation"),
        ]
        self.current_index = 0

    def update(self, stage_id: str, substep: str = None):
        for i, (sid, name, desc) in enumerate(self.stages):
            if sid == stage_id:
                self.current_index = i
                progress = int((i / len(self.stages)) * 100)
                self.callback({
                    "stage": stage_id,
                    "stage_name": name,
                    "stage_description": substep or desc,
                    "progress": progress,
                    "stages_completed": [s[0] for s in self.stages[:i]],
                })
                break
```

### Frontend: React Component

```tsx
// frontend/src/components/reports/ReportProgress.tsx

"use client";

import { useEffect, useState } from "react";

interface ProgressState {
  stage: string;
  stage_name: string;
  stage_description: string;
  progress: number;
  elapsed_seconds: number;
  stages_completed: string[];
  status: string;
}

const STAGES = [
  { id: "upload", name: "Upload Processing" },
  { id: "transcript", name: "Transcript Analysis" },
  { id: "survey", name: "Survey Processing" },
  { id: "executive", name: "Executive Summary" },
  { id: "conversation", name: "Conversation Analysis" },
  { id: "takeaways", name: "Key Takeaways" },
  { id: "quotes", name: "Quote Extraction" },
  { id: "survey_insights", name: "Survey Insights" },
  { id: "charts", name: "Chart Generation" },
  { id: "assembly", name: "PPTX Assembly" },
];

export function ReportProgress({ jobId, eventName }: { jobId: string; eventName: string }) {
  const [progress, setProgress] = useState<ProgressState | null>(null);
  const [startTime] = useState(Date.now());

  useEffect(() => {
    const eventSource = new EventSource(`/api/reports/jobs/${jobId}/progress`);

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setProgress(data);

      if (data.status === "completed" || data.status === "failed") {
        eventSource.close();
      }
    };

    return () => eventSource.close();
  }, [jobId]);

  if (!progress) {
    return <div className="animate-pulse">Connecting...</div>;
  }

  const elapsed = Math.floor((Date.now() - startTime) / 1000);
  const estRemaining = Math.max(0, Math.floor((elapsed / progress.progress) * (100 - progress.progress)));

  return (
    <div className="bg-white rounded-lg shadow-lg p-6 max-w-2xl mx-auto">
      {/* Header */}
      <h3 className="text-lg font-semibold text-gray-900 mb-4">
        Generating Report: "{eventName}"
      </h3>

      {/* Progress Bar */}
      <div className="relative h-4 bg-gray-200 rounded-full overflow-hidden mb-4">
        <div
          className="absolute h-full bg-gradient-to-r from-purple-600 to-cyan-500 transition-all duration-500 ease-out"
          style={{ width: `${progress.progress}%` }}
        />
        <span className="absolute inset-0 flex items-center justify-center text-xs font-medium text-white mix-blend-difference">
          {progress.progress}%
        </span>
      </div>

      {/* Current Stage */}
      <div className="flex items-center gap-2 mb-6">
        <span className="text-yellow-500 animate-pulse text-xl">⚡</span>
        <div>
          <p className="font-medium text-gray-900">{progress.stage_name}...</p>
          <p className="text-sm text-gray-500">{progress.stage_description}</p>
        </div>
      </div>

      {/* Stage Checklist */}
      <div className="bg-gray-50 rounded-lg p-4 mb-4">
        {STAGES.map((stage) => {
          const isCompleted = progress.stages_completed.includes(stage.id);
          const isCurrent = progress.stage === stage.id;

          return (
            <div key={stage.id} className="flex items-center gap-3 py-1">
              {isCompleted ? (
                <span className="text-green-500">✓</span>
              ) : isCurrent ? (
                <span className="text-blue-500 animate-pulse">●</span>
              ) : (
                <span className="text-gray-300">○</span>
              )}
              <span className={`text-sm ${isCompleted ? "text-gray-600" : isCurrent ? "text-gray-900 font-medium" : "text-gray-400"}`}>
                {stage.name}
              </span>
            </div>
          );
        })}
      </div>

      {/* Time Display */}
      <div className="flex justify-between text-sm text-gray-500 border-t pt-4">
        <span>Elapsed: {formatTime(elapsed)}</span>
        <span>Est. Remaining: ~{formatTime(estRemaining)}</span>
      </div>
    </div>
  );
}

function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}
```

---

## Preview Feature (Stretch Goal)

For real-time content preview, we could show:

1. **Executive Summary bullets** as they're generated
2. **Key Takeaways** appearing one by one
3. **Chart thumbnails** as they're created

This would require streaming LLM output, which is more complex but very impressive UX.

---

## Implementation Priority

1. **Phase 1:** Basic SSE progress streaming (backend)
2. **Phase 2:** Progress UI component (frontend)
3. **Phase 3:** Integrate with existing reports page
4. **Phase 4:** (Optional) Content preview streaming

---

## Alternative: Polling Approach

If SSE is problematic, fall back to polling:

```tsx
// Poll every 500ms instead of SSE
useEffect(() => {
  const interval = setInterval(async () => {
    const res = await fetch(`/api/reports/jobs/${jobId}`);
    const data = await res.json();
    setProgress(data);
    if (data.status === "completed" || data.status === "failed") {
      clearInterval(interval);
    }
  }, 500);
  return () => clearInterval(interval);
}, [jobId]);
```

This is simpler but uses more network requests.
