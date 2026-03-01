# Rubric (per case)

## Automated Checks (run every time)

### 1. JSON Validity
- Pass if output parses and matches schema
- Threshold: >= 99% of runs

### 2. Faithfulness
- Pass if every evidence quote appears verbatim in the cited review text
- Threshold: >= 98% of claims

### 3. Relevance (new)
- Pass if evidence quotes contain keywords consistent with the theme label
- Catches hallucinated theme labels backed by unrelated quotes
- Threshold: >= 95% of evidence items
- Note: only verifies known theme categories — unknown themes pass through

### 4. Sentiment Accuracy
- Always pass — sentiment is computed in code from ground truth labels, not by the model
- Should always be 100% exact match

## Manual Checks (run on 10–20 cases per prompt version)

### Theme Quality
- 2 = captures the real top themes (addictive, fun, ads, crashes, etc.)
- 1 = partial — gets some themes but misses obvious ones or mislabels
- 0 = misses obvious themes or hallucinates themes not in the data

### Evidence Quality
- 2 = quotes clearly support the theme, well chosen
- 1 = quotes are verbatim but loosely related to theme
- 0 = quotes are verbatim but irrelevant to theme (automated check should catch this)

### Summary Bullet Quality
- 2 = bullets give a clear, accurate executive picture of the reviews
- 1 = bullets are vague or repeat each other
- 0 = bullets contradict the data or are hallucinated

## Overall Pass Criteria
- Must pass JSON validity + Faithfulness to be considered "good"
- Relevance failures are warnings — investigate but do not auto-fail
- Manual theme quality score must be >= 1 to ship a prompt version
