# MediaHub Metadata Schema

Based on analysis of Release Schedules.xlsx and CHM Podcast Content Matrix.xlsx

---

## Data Hierarchy

```
Client (pharma company)
├── Projects (drug/program)
│   ├── KOL Groups (doctor pairings)
│   │   ├── Shoots (recording sessions)
│   │   │   ├── Full Podcast (Video)
│   │   │   ├── Full Podcast (Audio)
│   │   │   ├── Clips 1-N (Video, various aspect ratios)
│   │   │   └── Clips 1-N (Audio)
│   │   └── Schedule entries (per-week release plan)
│   └── Aggregate metrics
└── User access control
```

---

## Entity Metadata

### Client
| Field | Type | Source | Description |
|-------|------|--------|-------------|
| name | string | Manual | "AstraZeneca", "Daiichi Sankyo" |
| slug | string | Derived | URL-safe identifier |
| logo_url | string | Manual | Brand logo |
| primary_contact | string | Manual | Client contact person |
| is_active | bool | System | Active status |

### Project
| Field | Type | Source | Description |
|-------|------|--------|-------------|
| name | string | Sheet name | "Enhertu", "DB09", "Lymparza" |
| code | string | Derived | Short code for internal use |
| client_id | FK | Mapping | Parent client |
| description | text | Manual | Drug/program description |
| therapeutic_area | string | Manual | "Breast Cancer", "Oncology" |
| is_active | bool | System | Active status |

### KOL Group
| Field | Type | Source | Description |
|-------|------|--------|-------------|
| name | string | "KOL's" column | "Mouabbi/O'Shaughnessy/Rimawi" |
| project_id | FK | Sheet → Project | Parent project |
| video_count | int | "# of Videos" column | Total videos in cycle |
| publish_day | string | "Day" column | "Monday", "Tuesday", etc. |

### KOL (Doctor)
| Field | Type | Source | Description |
|-------|------|--------|-------------|
| name | string | Parsed from group | "Dr. Jason Mouabbi" |
| title | string | Manual | "MD", "PhD" |
| specialty | string | Manual | "Medical Oncology" |
| institution | string | Manual | Hospital/university |
| photo_url | string | Manual | Headshot |
| bio | text | Manual | Biography |

### Shoot (Recording Session)
| Field | Type | Source | Description |
|-------|------|--------|-------------|
| name | string | ops-console | Session name |
| shoot_date | datetime | ops-console | Recording date |
| project_id | FK | Mapping | Parent project |
| kol_group_id | FK | Mapping | KOL pairing |
| doctors[] | array | Legacy | Doctor names (deprecated) |
| diarized_transcript | text | ops-console | Full transcript |

### Clip
| Field | Type | Source | Description |
|-------|------|--------|-------------|
| title | string | ops-console | Clip title |
| description | text | ops-console | Description |
| clip_number | int | Content Matrix | 1, 2, 3... or null for full podcast |
| content_type | enum | Derived | "full_podcast", "clip" |
| media_type | enum | Derived | "video", "audio" |
| aspect_ratio | enum | Columns | "16x9", "9x16" |
| is_short | bool | Derived | True for 9x16 vertical |
| video_path | string | ops-console | Local file path |
| video_preview_url | string | ops-console | Thumbnail/preview |
| thumbnail_path | string | Content Matrix | Custom thumbnail |
| status | enum | System | draft, ready, scheduled, published |
| publish_at | datetime | Schedule | Planned publish date |
| published_at | datetime | Platform | Actual publish date |

### Post (Platform Publication)
| Field | Type | Source | Description |
|-------|------|--------|-------------|
| platform | string | ops-console | "youtube", "linkedin", "twitter" |
| provider_post_id | string | Platform API | Platform-specific ID |
| title | string | Platform | Post title |
| description | text | Platform | Post description |
| posted_at | datetime | Platform | When posted |
| view_count | int | Analytics | Views |
| like_count | int | Analytics | Likes/reactions |
| comment_count | int | Analytics | Comments |
| share_count | int | Analytics | Shares/reposts |
| impression_count | int | Analytics | Impressions |
| stats_synced_at | datetime | System | Last stats fetch |

### Schedule Entry (NEW - for release planning)
| Field | Type | Source | Description |
|-------|------|--------|-------------|
| kol_group_id | FK | Sheet row | Which KOL group |
| week_start | date | Column header | Week starting date |
| video_number | string | Cell value | "V1", "V2", "CLIP", etc. |
| aspect_16x9 | bool | Column presence | Has horizontal version |
| aspect_9x16 | bool | Column presence | Has vertical version |

---

## Mapping: Spreadsheet → Database

### Release Schedules.xlsx

| Sheet | Client | Project Code |
|-------|--------|--------------|
| Social Clips | CHM | SOCIAL |
| DB09 | Daiichi Sankyo | DB09 |
| Early Breast Cancer Daiichi | Daiichi Sankyo | EBC |
| TB02 | Daiichi Sankyo | TB02 |
| Enhertu | AstraZeneca | ENHERTU |
| Lymparza | AstraZeneca | LYMPARZA |
| Neratnib Puma | Puma | NERATINIB |

### KOL Groups (from all sheets)

| Group Name | Project | # Videos | Day |
|------------|---------|----------|-----|
| Mouabbi/O'Shaughnessey/Rimawi | DB09, SOCIAL | 5 | Monday |
| Kang/Bardia | DB09, SOCIAL | 8 | Monday |
| Iyengar/Dietrich | DB09, SOCIAL | 6 | Tuesday |
| Gadi/Rao | EBC | 5 | Monday |
| Conlin/McArthur | EBC | 6 | Wednesday |
| Iyengar/Jhaveri | EBC | 8 | Friday |
| Iyengar/Hamilton | TB02 | 6 | Tuesday |
| Pegram/Garrido-Castro | TB02 | 6 | Thursday |
| Gradishar/Traina | TB02 | 4 | Friday |
| Mouabbi Cairo | ENHERTU | 8 | Monday |
| Mouabbi Rimawi | ENHERTU | 8 | Tuesday |
| Hamilton/Vidal | ENHERTU | 4 | Wednesday |
| Iyengar/Robson | LYMPARZA | 8 | Wednesday |
| Mouabbi/Birhiray/Chang | NERATINIB | 8 | Thursday |

---

## UI Data Requirements

### Client Dashboard
- Total clips across all projects
- Total views, likes, comments (aggregated)
- Active projects count
- KOL count
- Performance trend (week-over-week)
- Top performing clips

### Project View
- KOL groups in this project
- Total clips per KOL group
- Release calendar/schedule
- Upcoming releases
- Published vs scheduled ratio
- Performance by KOL group

### KOL Group View
- Doctor profiles with photos
- Clips list with thumbnails
- Per-clip metrics
- Performance comparison across clips
- Release schedule for this group

### Clip Detail
- Video preview/player
- Full transcript (if available)
- Platform posts with metrics
- Engagement over time chart
- Related clips from same shoot

---

## API Endpoints Needed

```
# Client-scoped
GET /api/clients
GET /api/clients/{slug}
GET /api/clients/{slug}/analytics/summary
GET /api/clients/{slug}/analytics/timeline

# Project-scoped
GET /api/clients/{slug}/projects
GET /api/clients/{slug}/projects/{code}
GET /api/clients/{slug}/projects/{code}/analytics

# KOL Groups
GET /api/clients/{slug}/projects/{code}/kol-groups
GET /api/clients/{slug}/projects/{code}/kol-groups/{id}
GET /api/clients/{slug}/projects/{code}/kol-groups/{id}/clips

# Clips
GET /api/clients/{slug}/clips
GET /api/clients/{slug}/clips/{id}
GET /api/clients/{slug}/clips/{id}/posts

# KOLs (doctors)
GET /api/kols
GET /api/kols/{id}
```

---

## Frontend Component Structure (Atomic Design)

### Atoms
- `StatValue` - single metric display (views: 1.2M)
- `Badge` - status/tag indicator
- `Avatar` - KOL photo
- `Thumbnail` - clip preview image
- `ProgressBar` - engagement indicator

### Molecules
- `StatCard` - metric with label and trend
- `KOLChip` - avatar + name + specialty
- `ClipCard` - thumbnail + title + metrics
- `PlatformBadge` - platform icon + post status

### Organisms
- `StatsGrid` - multiple StatCards in responsive grid
- `KOLList` - list of KOL chips
- `ClipGallery` - grid of clip cards
- `PerformanceChart` - line/bar chart with metrics
- `ReleaseCalendar` - schedule visualization

### Templates
- `DashboardLayout` - header + sidebar + main content
- `DetailLayout` - breadcrumbs + hero + content sections

### Pages
- `ClientDashboard` - overview for a client
- `ProjectDetail` - project with KOL groups
- `KOLGroupDetail` - group with clips
- `ClipDetail` - single clip with all metadata
