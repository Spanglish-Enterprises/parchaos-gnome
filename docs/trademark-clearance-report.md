# Comprehensive Trademark & Trade Dress Clearance Report

**Date**: 2026-09-28  
**Scope**: Ticket #99 (Legal sweep task T21)  
**Target Marks**: "ParchaOS", "Parcha" (with Store, Browser, Dock, Controls), "Parcher"  
**Target Design**: Halved Passion Fruit Logo & ParchaOS Desktop Trade Dress  
**Classes Analyzed**: Class 9 (Computer Software / OS) & Class 42 (IT Services, Software as a Service)

---

## 1. Word Mark Clearance Analysis

### "ParchaOS" / "Parcha OS"
* **Global Trademark Registries (USPTO, EUIPO, WIPO)**: Zero registered or pending software marks for "ParchaOS".
* **Common Law / Industry Scan**:
  * Unrelated uses identified in music ("Parchaos" single/album) and local hospitality ("Parchao's" restaurant), representing entirely distinct classes of goods/services with no likelihood of consumer confusion.
  * **Parch Linux** (parchlinux.com): An Arch-based distribution active since ~2021. While "ParchaOS" is distinct, there is potential for confusion if shortened.
  * **Enforcement Rule**: **Never abbreviate "ParchaOS" to "Parch"** in repository names, package prefixes, documentation, or marketing. All packages must explicitly use `parchaos-` (e.g., `parchaos-desktop`, `parchaos-release`).
* **Conclusion**: **GO**. Low risk, highly distinctive and arbitrary for operating systems.

### "Parcha" (Component Brand: Store, Browser, Dock, Controls)
* **WIPO / USPTO**: No active Class 9 / 42 registrations.
* **Prior Uses**:
  * *Parcha / Parcha Labs* (parcha.ai): Previously an AI compliance platform for fintech. The company retired the "Parcha" name and rebranded to Grep AI; no active USPTO registration was maintained. Consumer desktop OS applications (Store, Browser, Dock) are in a different market channel.
* **Conclusion**: **GO**. Proceed with "Parcha" sub-branding.

### "Parcher" (File Manager)
* **Analysis**: Wordplay on "Parcha" + "Finder/Searcher".
* **Registries & GitHub/App Stores**: No conflicting software, desktop utilities, or file managers operate under the name "Parcher".
* **Conclusion**: **GO**. Clear for deployment.

---

## 2. Logo & Geometric Mark Clearance

### Visual Comparison & Geometry Sweeps
* **USPTO Serial 97350787 ("PASSIONFRUIT")**: Application filed in 2022 was formally abandoned / DEAD as of 2023-12-08 following sustained opposition. Standard-character word mark; not a design conflict.
* **WIPO Global Brand Database Findings**:
  * *Twilio Inc.*: Registered mark in Class 9, 38, 42 (US 8275202, EM, GB, JP, etc.) featuring a thick outer ring surrounding 4 dots.
  * *Japan Tobacco* ("Seven Circles", WO 1282335): Thick ring surrounding 7 dots (1 center + 6 radial), registered in Class 34.
  * *Yelp App/Circle Symbol*: At small interface dimensions (16px to 24px on a top panel / launcher menu), a symmetrical radial multi-dot or teardrop rosette in a ring can mimic the Yelp mobile icon.

### Design Revisions Implemented (Ticket T7 & Commit `1.0.0-6`)
To defeat both automated similarity crawlers and likelihood of confusion with Twilio, JT, and Yelp:
1. **The Indicator Gap**: An asymmetrical gap was cut into the outer rind border ring. This breaks closed-ring geometry and establishes a unique technical/stylized motif.
2. **Irregular Seed Placement**: Replaced symmetrical radial rosettes with non-uniform, organic teardrop seeds to eliminate radial symmetry.
3. **Asset Naming**: All system assets are strictly named `parchaos-logo.svg`, `parchaos-logo-symbolic.svg`, and `parchaos-launcher.svg` rather than generic names.
* **Conclusion**: **CLEARED**. The mark comfortably avoids third-party trademark silhouette claims and ring-and-dot registrations.

---

## 3. Trade Dress & Intellectual Property Review

Given ParchaOS's desktop workflow, a rigorous review of industry trade dress and utility/design patents was conducted:

| UI Element | Risk Level | Prior Art / Legal Basis | Mitigation / Status |
| :--- | :--- | :--- | :--- |
| **Halved Passion Fruit Mark** | **Very Low** | Does not feature trademark fruit silhouette, leaf, or bite geometry. | **Cleared** (irregular seeds + open rind gap). |
| **Dock Magnification** | **None / Cleared** | Trade dress & patent review: US Patent 7,434,177 expired in 2019/2020. | Prior art. Freely implementable in open-source software. |
| **Genie / Magic Lamp Minimize** | **None / Cleared** | Trade dress & patent review: US Patent 7,328,406 expired in 2019/2020. | Prior art. Freely implementable. |
| **Global Top Menu Bar** | **None / Cleared** | Generic UI paradigm dating back to Xerox Alto, Lisa, Amiga, and Atari ST. | Unprotectable generic UI paradigm. |
| **Traffic Light Window Buttons** | **Moderate to High** | Combination of Red (close), Yellow (minimize), Green (zoom) in top-left is recognized Apple trade dress. | **Ticket #111**: Formally adopt ParchaOS brand colors (violet/yellow/plum palette) for window controls. |

---

## 4. Final Recommendations & Go Decision

1. **Brand Registration**: Proceed with formal USPTO / EUIPO Class 9 & Class 42 trademark application for **"ParchaOS"** and the **Halved Passion Fruit Logo**.
2. **Namespace Policy**: Maintain strict enforcement of the `parchaos-` naming prefix in all RPM packages, COPR repos, and documentation to avoid collision with Parch Linux.
3. **Window Buttons**: Implement Ticket #111 before public general availability to completely clear desktop trade dress risk.
