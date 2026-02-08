# Wiki Content Directory

This directory contains the source files for the SuperLocalMemory V2 GitHub Wiki.

## 🎯 Purpose

**Single Source of Truth:** Edit wiki pages here in the main repository, then sync to GitHub Wiki using the automated sync tool.

## 📂 Structure

```
wiki-content/
├── Home.md                          # Wiki home page
├── _Sidebar.md                      # Navigation sidebar
├── _Footer.md                       # Footer (all pages)
├── Installation.md                  # Setup guide
├── Quick-Start-Tutorial.md          # Getting started
├── CLI-Cheatsheet.md                # Command reference
├── Universal-Architecture.md        # System architecture
├── MCP-Integration.md               # MCP setup (16+ IDEs)
├── Universal-Skills.md              # Skills documentation
├── Knowledge-Graph-Guide.md         # Graph system
├── Pattern-Learning-Explained.md    # Pattern learning
├── Multi-Profile-Workflows.md       # Profile management
├── Python-API.md                    # API reference
├── Configuration.md                 # Config options
├── Comparison-Deep-Dive.md          # vs Mem0, Zep, etc.
├── Why-Local-Matters.md             # Privacy benefits
├── FAQ.md                           # Frequently asked questions
└── Roadmap.md                       # Version history & plans
```

## 🔄 Workflow: How to Update Wiki

### Option 1: Automated Sync (Recommended)

1. **Edit** wiki pages in `wiki-content/` directory
2. **Commit** changes to main repo:
   ```bash
   git add wiki-content/
   git commit -m "Docs: Update wiki pages"
   git push origin main
   ```
3. **Sync** to GitHub Wiki:
   ```bash
   ./sync-wiki.sh
   ```

### Option 2: Manual Sync

```bash
# Clone wiki repo (first time only)
git clone https://github.com/varun369/SuperLocalMemoryV2.wiki.git /tmp/wiki

# Copy files
cp wiki-content/*.md /tmp/wiki/

# Commit and push
cd /tmp/wiki
git add .
git commit -m "Update wiki"
git push origin master
```

## ⚙️ Automated Sync Tool

**Script:** `sync-wiki.sh` (in repo root)

**What it does:**
- Clones/updates the wiki repository
- Syncs all `.md` files from `wiki-content/` to wiki repo
- Excludes internal docs (DEPLOYMENT-CHECKLIST.md, etc.)
- Commits and pushes to GitHub Wiki automatically

**Usage:**
```bash
./sync-wiki.sh
```

**Git Hook:**
A post-commit hook automatically reminds you to sync when wiki-content/ is modified.

## 🌐 GitHub Wiki vs wiki-content/

**Why separate?**
GitHub Wiki is a **separate git repository** at:
```
https://github.com/varun369/SuperLocalMemoryV2.wiki.git
```

This is how GitHub works - we didn't choose this, it's GitHub's design.

**Why wiki-content/ in main repo?**
✅ Single source of truth (all docs in one repo)
✅ Version control alongside code
✅ Easy to edit (same repo as code)
✅ Automated sync keeps them in sync
✅ CI/CD can validate wiki changes
✅ No confusion - edit here, sync with script

## 🤖 AI Agent Workflow

**For Claude Code or other AI agents:**

1. **Edit wiki pages:** Always edit files in `wiki-content/` directory
2. **After editing:** Run `./sync-wiki.sh` to deploy to GitHub Wiki
3. **Verify:** Check https://github.com/varun369/SuperLocalMemoryV2/wiki

**Never edit the wiki directly on GitHub** - changes will be overwritten by sync.

## 📋 Checklist: Adding New Wiki Page

1. Create `wiki-content/New-Page-Name.md`
2. Add to `wiki-content/_Sidebar.md` for navigation
3. Link from `wiki-content/Home.md` if appropriate
4. Add internal links (3-5 links to other wiki pages)
5. Include SEO keywords in first paragraph
6. Add creator attribution footer
7. Commit to main repo
8. Run `./sync-wiki.sh`
9. Verify on GitHub Wiki

## 🔍 SEO Best Practices

Each wiki page should have:
- ✅ Keywords in first paragraph
- ✅ Proper H1/H2/H3 structure
- ✅ 3-5 internal links to other wiki pages
- ✅ Code examples where appropriate
- ✅ Creator attribution: "Created by Varun Pratap Bhardwaj"

## 🚫 Files NOT Synced to Wiki

These files stay in main repo only (excluded from sync):
- `DEPLOYMENT-CHECKLIST.md` (internal)
- `WIKI-UPDATE-SUMMARY.md` (internal)
- `NEW-PAGES-SUMMARY.md` (internal)
- `README.md` (this file - main repo only)

## 📊 Current Status

- **Total wiki pages:** 17
- **Word count:** 50,000+
- **Code examples:** 100+
- **Internal links:** 50+
- **Last sync:** 2026-02-07
- **Status:** ✅ Zero broken links

## 🔗 Useful Links

- **Wiki:** https://github.com/varun369/SuperLocalMemoryV2/wiki
- **Wiki Repo:** https://github.com/varun369/SuperLocalMemoryV2.wiki.git
- **Main Repo:** https://github.com/varun369/SuperLocalMemoryV2

## 🆘 Troubleshooting

**Problem: Sync fails with authentication error**
- Solution: Ensure you have push access to the wiki repo
- Check: `git config --global user.name` and `git config --global user.email`

**Problem: Changes not showing on GitHub Wiki**
- Solution: Wait 1-2 minutes for GitHub to rebuild
- Verify: Check https://github.com/varun369/SuperLocalMemoryV2/wiki

**Problem: Merge conflicts in wiki repo**
- Solution: Delete `/tmp/SuperLocalMemoryV2.wiki` and re-run sync script

## 💡 Pro Tips

1. **Always edit in wiki-content/**, never directly on GitHub Wiki
2. **Run sync-wiki.sh after every wiki change**
3. **Use markdown preview** to check formatting before committing
4. **Test internal links** with `[[Page-Name]]` format
5. **Keep pages focused** - one topic per page
6. **Cross-link pages** - helps SEO and navigation

---

**Created by:** Varun Pratap Bhardwaj (Solution Architect)
**Project:** SuperLocalMemory V2
**License:** MIT
**Last Updated:** February 7, 2026
