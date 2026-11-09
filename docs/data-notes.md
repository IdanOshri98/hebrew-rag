# Data Exploration Notes

## 1. Dataset Overview

**Project:** Travel & Culture RAG

**Source:** English Wikipedia (MediaWiki API)

**Format:** JSON

**Storage:** `data/raw/`

**Target dataset size:** 50 articles

Each JSON file contains the following fields:

| Field | Description |
|---|---|
| `pageid` | Unique Wikipedia page identifier |
| `title` | Article title |
| `url` | Link to the original Wikipedia article |
| `content` | Extracted plain-text article content |
| `fetched_at` | Timestamp of data retrieval |

The dataset covers cities, landmarks, history, culture, and natural attractions.

## 2. Documents Inspected

Ten articles were selected for structural analysis:

| Article | Category | Main Topics |
|---|---|---|
| Madrid | City | History, Geography, Culture, Economy, Transport |
| Tokyo | City | History, Geography, Tourism, Culture, Transportation |
| Rome | City | History, Architecture, Culture, Tourism |
| Eiffel Tower | Landmark | History, Design, Dimensions, Tourism |
| Colosseum | Landmark | History, Physical Description, Historical Use |
| Sagrada Família | Landmark | Pending heading inspection |
| Flamenco | Culture | History, Music, Dance, Cultural Origins |
| Renaissance | History | Origins, Humanism, Art, European Influence |
| Grand Canyon | Nature | Geography, Geology, Wildlife, Tourism |
| Mount Fuji | Nature | Geography, Geology, Climbing, Cultural Significance |

The headings of nine articles were inspected directly. Sagrada Família replaced Prado Museum and still requires a heading inspection.

## 3. Document Structure

### 3.1 Headings

Wikipedia extracts preserve section headings using a consistent text format.

Examples:

- `== History ==` — main section
- `=== Middle Ages ===` — subsection
- `==== Tourism ====` — nested subsection

These headings make it possible to identify logical sections programmatically.

### 3.2 Paragraphs

- Articles contain plain English text.
- Paragraphs are generally separated by blank lines.
- Some sections contain very long paragraphs.
- Article length and section structure vary significantly.

### 3.3 Differences Between Article Types

City articles typically contain sections about history, geography, economy, culture, and transportation.

Landmark articles focus more on construction, design, historical significance, and tourism.

Cultural and historical articles have more specialized structures.

Natural attractions include geography, geology, ecology, and visitor activities.

Therefore, preprocessing should not depend on a fixed set of section names.

### 3.4 Tables and Formatting

The API returns plain text rather than the original webpage HTML.

- HTML formatting is not preserved.
- Tables are not preserved as structured tables.
- Some lists may be incomplete after extraction.
- Section headings and paragraph boundaries remain useful.

## 4. Noise and Irrelevant Content

Several recurring sections were identified:

- `See also`
- `References`
- `Notes`
- `Bibliography`
- `External links`
- `Further reading`
- `Sources`

These sections often contain navigation information, citations, or lists of resources rather than explanatory article content.

### Example: Madrid

At the end of the Madrid article, the following sections were observed:

- See also
- References
- Notes
- Citations
- Bibliography
- External links

Some lists, such as twin towns and sister cities, also appeared incomplete.

These observations suggest that certain sections can be removed during preprocessing.

## 5. Data Quality Issues

During inspection, the original `Prado Museum.json` file was found to contain an empty `content` field.

The ingestion script previously allowed empty content because it used a default empty string when extracting text.

A validation check was added to prevent saving empty documents.

The problematic article was replaced in the inspection set with Sagrada Família, an article already included in the original dataset.

### Lessons Learned

- A successful API response does not guarantee useful content.
- Existing JSON files may contain empty or incomplete text.
- Data validation is necessary before generating embeddings.
- Document quality should be checked before indexing.

## 6. Proposed Cleaning Strategy

The following decisions will guide the preprocessing stage.

### Preserve

- Article titles
- Meaningful section headings
- Factual paragraphs
- Relevant historical and cultural information
- Source URLs and page identifiers

### Remove or Normalize

- Reference and navigation sections where appropriate
- Excessive blank lines
- Unnecessary whitespace
- Empty sections
- Formatting artifacts

### Validation

Before processing an article:

1. Verify that the JSON file can be loaded.
2. Verify that `content` is not empty.
3. Check that meaningful text is present.
4. Preserve metadata for source attribution.

These are proposed preprocessing rules, not transformations already implemented.

## 7. Chunking Considerations

The article structure suggests using **section-aware chunking**.

Instead of splitting documents at arbitrary positions, the system can use section headings as natural boundaries.

For example, the Madrid article contains separate sections for History, Culture, Economy, and Transport.

A user asking about Madrid's nightlife should ideally retrieve text from the relevant Culture subsection.

### Proposed Approach

1. Identify section headings.
2. Split articles into logical sections.
3. Divide long sections into smaller chunks.
4. Preserve the article title and section heading as metadata.
5. Avoid creating empty or extremely short chunks.

The exact chunk size and overlap will be determined during implementation and testing.

## 8. Golden Questions

Golden questions will be used later to evaluate retrieval accuracy and answer quality.

Each inspected article has three candidate questions.

### Madrid

1. What are the main tourist attractions in Madrid?
2. What is Madrid's population?
3. When did Madrid become the seat of the Spanish royal court?

### Tokyo

1. What are the main tourist attractions in Tokyo?
2. What natural disasters affect Tokyo?
3. What is Tokyo known for culturally?

### Rome

1. What are the main historical landmarks in Rome?
2. How did Rome develop during the Roman Empire?
3. What are the most important aspects of Roman cuisine?

### Eiffel Tower

1. When was the Eiffel Tower built?
2. How tall is the Eiffel Tower?
3. How many levels can visitors access?

### Colosseum

1. When was the Colosseum constructed?
2. What was the Colosseum originally used for?
3. How is the Colosseum used today?

### Sagrada Família

1. When did construction of the Sagrada Família begin?
2. Who designed the Sagrada Família?
3. What makes its architecture unique?

### Flamenco

1. Where did flamenco originate?
2. What are the main elements of flamenco?
3. When did UNESCO recognize flamenco?

### Renaissance

1. Where did the Renaissance begin?
2. What is Renaissance humanism?
3. How did the Renaissance influence European art?

### Grand Canyon

1. How was the Grand Canyon formed?
2. What activities can tourists do at the Grand Canyon?
3. What wildlife can be found at the Grand Canyon?

### Mount Fuji

1. How tall is Mount Fuji?
2. What are the main climbing routes on Mount Fuji?
3. What is the cultural significance of Mount Fuji in Japan?

**Important:** These are candidate evaluation questions. Their answers must be verified against the stored documents before they are used as a final evaluation dataset.

## 9. Chunking Implementation & Results

### Dataset
- Documents processed: 408
- Total chunks generated: 3,382
- Average chunk size: 336.1 tokens
- Output file: `data/chunks.jsonl`

### Implementation
- Documents are split by Markdown headings (`##`).
- Long sections are split by paragraphs, then sentences and words when necessary.
- Maximum chunk size: 600 tokens.
- Target overlap: approximately 50 tokens between consecutive chunks within the same section.
- Token counting uses `tiktoken` with `cl100k_base`.
- Each chunk contains: `id`, `text`, `title`, `url`, `section`, `n_tokens`.
- Embedded MediaWiki chart-style artifacts were filtered during chunk processing.

### Validation Results
- Unique chunk IDs: 3,382 / 3,382
- Missing metadata fields: 0
- Empty chunks: 0
- Chunks exceeding 600 tokens: 0

### Known Limitations
- Token-based overlap can begin in the middle of a word or sentence.
- Some chunks are shorter than the target size to preserve section boundaries.
- Chunking quality will be evaluated during the retrieval evaluation stage.

## 10. Conclusions

The collected Wikipedia articles provide a useful starting dataset for a Travel & Culture RAG system.

The main findings are:

- Most inspected articles have a clear heading hierarchy.
- Different article categories require flexible processing.
- Several navigation and reference sections can introduce unnecessary noise.
- Empty documents must be detected and excluded.
- Section headings can support more meaningful chunking.

**Next step:** Next step: Generate embeddings for the 3,382 chunks, store them in Supabase pgvector, and implement semantic retrieval.