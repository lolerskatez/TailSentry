You are reviewing this entire codebase. Your goals:

1. **Completeness & Functionality**
   - Verify that the codebase is self-contained and functional.  
   - Flag any missing modules, dependencies, or configs that prevent proper execution.  
   - Check for inconsistencies in naming, imports, or unused variables.

2. **File/Folder Structure Audit**
   - List all files and folders, categorizing by purpose (config, frontend, backend, utils, assets, docs, tests, etc.).  
   - Identify redundant, outdated, or unused files and recommend removal.  
   - Suggest merging overly fragmented files into fewer, well-structured modules if applicable.

3. **Code Quality & Maintainability**
   - Highlight duplicate logic that should be consolidated.  
   - Check for inconsistent patterns (e.g., multiple approaches to the same task).  
   - Recommend compartmentalization: determine if refactoring into clear feature-based modules or services would improve maintainability.  

4. **Execution of Refactoring**
   - Propose a step-by-step cleanup plan:
     - Safe deletions (with reasoning).  
     - File merges or renames.  
     - Structural changes (e.g., grouping related logic into `services/`, `components/`, `api/`).  
     - Dependency cleanup (remove unused libraries).  

5. **Final Output**
   - Provide a concise report including:
     - ✅ Files to keep
     - 🗑️ Files to delete
     - 🔄 Files to merge/refactor
     - 📦 Suggested new structure
   - Ensure suggestions preserve functionality and stability.

Act like a senior code auditor. Be opinionated: don’t just describe, **decide and recommend**.
