---
notion_page_id: 2c9c95e7-d72e-81d8-ba46-e8a7ba0027d8
notion_url: https://www.notion.so/sample-2c9c95e7d72e81d8ba46e8a7ba0027d8
title: sample
uploaded: 2025-12-14T12:09:05.250374
---

# Sample Markdown Document

This is an example markdown file showing all supported formatting features.

## Text Formatting

You can use **bold**, *italic*, ***bold italic***, ~~strikethrough~~, and `inline code`.

### Links

- [External link](https://www.example.com)
- [Link with **bold** text](https://www.example.com)

## Lists

### Bulleted List
- First item
- Second item
  - Nested item (note: nesting not fully supported in Notion API)
- Third item

### Numbered List
1. First item
2. Second item
3. Third item

### To-Do List
- [ ] Incomplete task
- [x] Completed task
- [ ] Another task

## Code Blocks

Inline code: `const x = 42`

Code block with syntax highlighting:

```javascript
function hello(name) {
  console.log(`Hello, ${name}!`);
  return true;
}
```

Python example:

```python
def calculate_sum(a, b):
    """Calculate the sum of two numbers."""
    return a + b

result = calculate_sum(10, 20)
print(f"Result: {result}")
```

## Quotes

> This is a quote block.
> It can span multiple lines.

## Tables

| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| Row 1, Col 1 | Row 1, Col 2 | Row 1, Col 3 |
| Row 2, Col 1 | Row 2, Col 2 | Row 2, Col 3 |
| Row 3, Col 1 | Row 3, Col 2 | Row 3, Col 3 |

Tables with formatting:

| Feature | Status | Notes |
|---------|--------|-------|
| **Bold** | ✅ | Fully supported |
| *Italic* | ✅ | Fully supported |
| `Code` | ✅ | Fully supported |
| [Links](https://example.com) | ✅ | Fully supported |

## Dividers

Use three dashes for a divider:

---

## Mixed Content

You can combine **bold with [links](https://example.com)** and `inline code`.

### Advanced Example

Here's a realistic documentation example:

**API Endpoint:** `POST /api/users`

**Request Body:**
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "role": "admin"
}
```

**Response:**
- Success: Returns `201 Created` with user object
- Error: Returns `400 Bad Request` with error message

---

## Notes

- ✅ This document demonstrates all supported markdown features
- 🔄 Upload it to Notion to see the formatting preserved
- 📝 After upload, the file will have YAML frontmatter added automatically
