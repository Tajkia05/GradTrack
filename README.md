# GradTrack: Graduate Degree Progress & Milestone Management System

## Overview

GradTrack is a web-based platform that helps graduate students, faculty advisors, committee members, and graduate program administrators track and manage graduate degree milestones and academic progress. The initial use case is a Computer Science PhD program, modeled on UAlbany-style requirements.

Instead of tracking requirements across scattered documents, emails, and meetings, GradTrack centralizes the workflow: it encodes prerequisites, deadlines, role-based permissions, and status transitions, and automatically updates a student's progress as approvals are recorded.

## Problem

Graduate students must complete many requirements over several years — coursework, advisor selection, comprehensive exams, committee formation, research proposals, candidacy, dissertation defense, and recurring progress reports. Requirements aren't strictly linear (e.g., the comprehensive exam can be completed before all coursework is done), so a simple checklist isn't enough. GradTrack represents this partial ordering, routes submissions to the right reviewer, and preserves a record of decisions.

The prototype does not connect to official university systems and does not make academic decisions automatically (e.g., transfer-credit equivalency remains a human decision).

## Users

- **Graduate Student** — views progress, submits milestones/documents, manages committee, submits transfer-credit requests.
- **Faculty Advisor / Committee Member** — reviews assigned submissions, approves/requests revisions, monitors students.
- **Graduate Program Director / Coordinator** — reviews administrative requests (e.g., transfer credit), manages program requirements, monitors students.


## Proposed Technologies

| Component | Technology | Reason |
|---|---|---|
| Front-end | React | Component-based UI, strong ecosystem for a multi-role app |
| Back-end | Python + FastAPI | Matches team's Python background; built-in validation and auto-generated API docs |
| Database | PostgreSQL | Well suited to relational data (users, milestones, committees, approvals) |
| Version Control / CI | Git/GitHub | Team experience; supports collaboration and PR-based workflow |
| Wireframes | Figma / Claude Design | Rapid iteration before implementation |

## Architecture

GradTrack follows a layered client-server architecture (React client → FastAPI server → PostgreSQL), organized internally as a modular monolith: separate modules for Student, Faculty/Review, Transfer Credit, Committee, and Rules/Eligibility, all running as one deployed application against one shared database. This fits the team's shared-schema workflow and the tightly coupled nature of the features (e.g., milestone eligibility depends on committee status and advisor declaration).

## Team

| Member | Primary Module | Relevant Skills |
|---|---|---|
| Tajkia Nuri Ananna | Student Experience | JavaScript, React, Tailwind CSS, Java, Python, PHP, SQL |
| Irien Akter | Faculty & Milestone Review | C, C++, Java, Python, HTML/CSS, JavaScript, SQL, MongoDB, Django |
| Elias Sanchez | Graduate Program Director & Transfer Credit Review | React, C#, .NET, Python, JavaScript, PostgreSQL, Azure Cloud |

