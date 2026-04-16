# Semptify Agent Guide

This repository contains a housing-rights and tenant-support product. Any AI agent working here should follow these standards.

> Canonical project governance and doc hierarchy are defined in `PROJECT_BIBLE.md`.

## Core Mission

Semptify is built to better protect the rights of humans facing housing problems.
It is for people who may not be able to afford a legal team, may be overwhelmed, and may need help organizing documents, evidence, timelines, and next steps.

## Non-Negotiables

- Free forever.
- No advertising ever.
- Privacy-respecting by design.
- User-controlled documents and storage wherever possible.
- Evidence preservation over feature novelty.
- Calm, clear, trustworthy UX.

## Truth Standard

- Semptify is about truth from both perspectives.
- Do not assume tenant claims are automatically true.
- Do not assume landlord claims are automatically true.
- Build for facts, records, chronology, and evidence.
- Do not support deceptive, retaliatory, or manipulative flows.

## AI Behavior Standards

- Give plain-language guidance.
- Optimize for stressed users with limited time, money, and attention.
- Avoid dark patterns, growth-hack framing, ad logic, or engagement bait.
- Avoid introducing features that depend on surveillance, analytics, or user profiling.
- Keep legal boundaries clear: organization and education are acceptable; unsupported legal-advice claims are not.

## Architecture Preference

- Prefer objects, qualifiers, functions, sequences, processes, and output objects as the structural model.
- Treat pages as UI surfaces generated from process needs, not as the deepest source of truth.
- Keep policy and transition logic centralized rather than duplicated across routers or templates.
- Favor strict serial gating for high-stakes workflows where later steps must not run before earlier steps complete.

## Product Decision Filter

When choosing between options, prefer the one that best improves:

1. Rights protection
2. Evidence integrity
3. User control
4. Clarity under stress
5. Privacy
6. Honest representation of system capabilities

Reject or challenge changes that primarily optimize for:

1. Monetization
2. Advertising
3. Vanity UX over usability
4. Hidden state that weakens auditability
5. Complexity without workflow benefit

## Repo Guidance

- Keep implementation consistent with public promises made in welcome, about, and privacy materials.
- If a proposed change creates a mismatch between product claims and actual behavior, flag it.
- Prefer deterministic, testable, auditable code paths.
- Preserve user trust as a first-order engineering concern.