# Accessibility Features - SuperLocalMemory V2.6.5

**Last Updated:** February 16, 2026
**Author:** Varun Pratap Bhardwaj

---

## Overview

SuperLocalMemory V2.6.5 includes comprehensive keyboard navigation and screen reader support for the interactive knowledge graph, making it fully accessible to users with disabilities.

## Keyboard Navigation

### Graph Container Focus

The graph container (`#graph-container`) is focusable via keyboard:

- **Focus method:** Click graph OR press `Tab` from controls above
- **Visual indicator:** Browser native focus outline + first node highlighted with blue border
- **ARIA role:** `role="application"` signals custom keyboard handling

### Node Navigation

| Key | Action |
|-----|--------|
| **Tab** | Move to next node (cycles through all nodes) |
| **Shift+Tab** | Move to previous node |
| **→** (Right Arrow) | Move to nearest node on the right |
| **←** (Left Arrow) | Move to nearest node on the left |
| **↓** (Down Arrow) | Move to nearest node below |
| **↑** (Up Arrow) | Move to nearest node above |
| **Home** | Jump to first node |
| **End** | Jump to last node |

**Arrow Key Algorithm:**
- Finds nodes in specified direction (based on X/Y coordinates)
- Prioritizes nodes closer to current position
- Combines Euclidean distance with directional score
- Ensures no "stuck" states (always finds a valid next node)

### Actions

| Key | Action |
|-----|--------|
| **Enter** or **Space** | Open modal for focused node |
| **Escape** | Clear active filter OR blur graph (if no filter) |

### Visual Focus Indicator

Focused nodes have the CSS class `.keyboard-focused` with:

```css
border-width: 5px;
border-color: #0066ff;
border-style: solid;
box-shadow: 0 0 15px #0066ff;
```

The graph smoothly animates to center the focused node in the viewport.

---

## Screen Reader Support

### ARIA Attributes

#### Graph Container

```html
<div id="graph-container"
     role="application"
     aria-label="Interactive knowledge graph - use Tab to navigate nodes, Enter to view details, Arrow keys to move between adjacent nodes, Escape to clear filters"
     aria-describedby="graph-stats">
</div>
```

- **`role="application"`** - Signals custom keyboard handling
- **`aria-label`** - Provides usage instructions
- **`aria-describedby`** - Links to graph statistics (node/edge count)

#### Status Regions

```html
<div id="graph-status-full" role="status" aria-live="polite">
    Showing all memories
</div>

<div id="graph-status-filtered" role="status" aria-live="polite">
    Viewing Cluster X (Y memories)
</div>
```

- **`role="status"`** - Semantic status information
- **`aria-live="polite"`** - Announces changes when user is idle

#### Hidden Status Region

An off-screen status region announces keyboard navigation events:

```html
<div id="graph-sr-status"
     role="status"
     aria-live="polite"
     aria-atomic="true"
     style="position:absolute; left:-10000px; width:1px; height:1px; overflow:hidden;">
</div>
```

This element is invisible but screen readers announce its content changes.

#### Buttons

All interactive buttons have `aria-label` attributes:

```html
<button aria-label="Refresh graph data">...</button>
<button aria-label="Clear filter and show all memories">...</button>
<button aria-label="Toggle dark mode">...</button>
```

#### Dropdowns

Form controls have proper labels:

```html
<label for="graph-layout-selector">Layout Algorithm:</label>
<select id="graph-layout-selector" aria-label="Select graph layout algorithm">
```

### Screen Reader Announcements

The `updateScreenReaderStatus()` function announces:

1. **Graph load:** "Graph loaded with X memories and Y connections"
2. **Node navigation:** "Memory 123: SuperLocalMemory Project, Cluster 2, Importance 8 out of 10"
3. **Filter cleared:** "Filters cleared, showing all memories"

These announcements are sent to the hidden `#graph-sr-status` region.

---

## Modal Focus Management

### Opening Modal

When `openMemoryModal()` is called:

1. **Store last focused element:** `window.lastFocusedElement = document.activeElement`
2. **Bootstrap modal shown event:** Focus moves to first button in modal
3. **Tab order:** Close button → Modal content → Action buttons → Footer buttons

### Closing Modal

When modal closes (via Bootstrap `hidden.bs.modal` event):

1. **Restore focus:** `window.lastFocusedElement.focus()`
2. **Clear stored element:** `window.lastFocusedElement = null`
3. **User can continue:** Keyboard navigation resumes from same node

This ensures users don't lose their place in the graph when opening/closing modals.

---

## Skip Links

A skip link is provided for keyboard users:

```html
<a href="#memories-pane" class="visually-hidden-focusable">Skip to Memories list</a>
```

This link is invisible until focused (via Tab), allowing users to bypass the graph and jump directly to the Memories tab.

---

## Testing with Screen Readers

### macOS VoiceOver

1. **Enable:** Press `Cmd+F5`
2. **Navigate:** `Control+Option+Arrow keys`
3. **Read current element:** `Control+Option+A`
4. **Test focus:** Tab through graph → Verify announcements

### Windows NVDA

1. **Install:** Download from [nvaccess.org](https://www.nvaccess.org/)
2. **Start:** `Control+Alt+N`
3. **Navigate:** Arrow keys
4. **Browse mode:** Press `Insert+Space` to toggle

### Windows JAWS

1. **Commercial software:** Most widely used screen reader
2. **Navigate:** Arrow keys + Tab
3. **Read mode:** Virtual cursor navigation

### Linux Orca

1. **Enable:** `Alt+F2`, type "orca"
2. **Configure:** `orca --setup`
3. **Navigate:** Arrow keys

---

## Compliance

### WCAG 2.1 AA Compliance

| Criterion | Status | Implementation |
|-----------|--------|----------------|
| **1.3.1 Info and Relationships** | ✅ Pass | Semantic HTML, ARIA roles |
| **2.1.1 Keyboard** | ✅ Pass | Full keyboard navigation |
| **2.1.2 No Keyboard Trap** | ✅ Pass | Escape key blurs graph |
| **2.4.3 Focus Order** | ✅ Pass | Logical tab order |
| **2.4.7 Focus Visible** | ✅ Pass | Blue outline on focused nodes |
| **3.2.1 On Focus** | ✅ Pass | No unexpected context changes |
| **4.1.2 Name, Role, Value** | ✅ Pass | ARIA labels on all controls |
| **4.1.3 Status Messages** | ✅ Pass | aria-live regions |

### Section 508 Compliance

- ✅ **(a) Keyboard access** - All graph functions accessible via keyboard
- ✅ **(c) Color contrast** - Blue focus indicator meets 4.5:1 contrast ratio
- ✅ **(d) Screen reader compatible** - ARIA labels and live regions

---

## Developer Notes

### Code Location

- **Keyboard navigation:** `/ui/js/graph-cytoscape.js` (lines 950-1150)
- **Modal focus management:** `/ui/js/modal.js` (lines 10-18, 142-160)
- **ARIA attributes:** `/ui/index.html` (graph-pane section)

### Key Functions

| Function | Purpose |
|----------|---------|
| `setupKeyboardNavigation()` | Attaches keyboard event handlers to graph container |
| `focusNodeAtIndex(index)` | Highlights node and centers viewport |
| `moveToAdjacentNode(direction, currentNode)` | Finds nearest node in specified direction |
| `announceNode(node)` | Sends node info to screen reader |
| `updateScreenReaderStatus(message)` | Updates hidden status region |

### Global State Variables

```javascript
var focusedNodeIndex = 0;              // Currently focused node index
var keyboardNavigationEnabled = false; // Is keyboard nav active?
var lastFocusedElement = null;         // For modal focus return
```

### Cytoscape.js Style Class

```javascript
{
    selector: 'node.keyboard-focused',
    style: {
        'border-width': 5,
        'border-color': '#0066ff',
        'border-style': 'solid',
        'box-shadow': '0 0 15px #0066ff'
    }
}
```

---

## Future Enhancements (v2.7+)

1. **Voice commands:** Integrate Web Speech API for voice navigation
2. **Braille support:** Test with refreshable Braille displays
3. **High contrast mode:** Additional theme for low vision users
4. **Keyboard shortcuts help:** Press `?` to show keyboard shortcuts overlay
5. **Focus trapping in modal:** Prevent Tab from leaving modal when open

---

## Feedback

If you encounter accessibility issues, please report them:

- **GitHub Issues:** https://github.com/varun369/SuperLocalMemoryV2/issues
- **Label:** Use `accessibility` tag
- **Include:** Browser, screen reader (if applicable), and steps to reproduce

---

**Copyright © 2026 Varun Pratap Bhardwaj - MIT License**
