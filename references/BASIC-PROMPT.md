Review Text:
{TEXT}

Available Images:
{IMAGES}

Task: Your task is to convert this text into Basic Note Type (front/back) Anki flashcards. Generate {TARGET} flashcards. Prioritize information regarding the imaging features of diseases, unique imaging findings, and methods of differentiating similar disease entities. Ensure that each flashcard is clearly written, and adheres to the specified formatting and reference criteria.

When an available image (figure, diagram, radiology image) is directly relevant to a flashcard, include it on the Back side using Anki's HTML image syntax: `<img src="filename.png">`. Place the `<img>` tag after the answer text, on its own line. Only reference images that are listed in Available Images. Do not reference images that are not present.

Formatting Criteria:
- Construct a table with three columns: "Front", "Back", "Number".
- Each row of the "Front" column should contain a single question testing the imaging features of disease, unique imaging findings, and methods of differentiating similar disease entities.
- The "Back" column should contain the succinct answer to the question in the corresponding row of the "Front" column.
- The "Number" column will serve to number each row, facilitating feedback.

Reference Criteria for each "Statement":
- Each flashcard should test a single concept
- Limit the word count of each question to less than 40 words.
- Each flashcard MUST be able to stand alone. Include the subject of the flashcard somewhere in the text.
- Keep ONLY simple, direct questions in the "Front" column.

Example:

| Front | Back | Number |
| --- | --- | --- |
| How is necrotic tissue identified in acute pancreatitis on a CT scan? | Lack of contrast enhancement. | 1 |
