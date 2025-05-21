document.addEventListener('DOMContentLoaded', () => {
    const documentUpload = document.getElementById('documentUpload');
    const uploadButton = document.getElementById('uploadButton');
    const uploadStatus = document.getElementById('uploadStatus');
    const queryInput = document.getElementById('queryInput');
    const askButton = document.getElementById('askButton');
    const synthesizedAnswerDiv = document.getElementById('synthesizedAnswer');
    const documentResponsesTableBody = document.querySelector('#documentResponsesTable tbody');

    const BACKEND_BASE_URL = "http://localhost:8000"; // Make sure your backend is running here

    // --- Document Upload Logic ---
    uploadButton.addEventListener('click', async () => {
        const files = documentUpload.files;
        if (files.length === 0) {
            uploadStatus.textContent = "Please select files to upload.";
            return;
        }

        uploadStatus.textContent = "Uploading files...";
        const formData = new FormData();
        for (let i = 0; i < files.length; i++) {
            formData.append('files', files[i]);
        }

        try {
            const response = await fetch(`${BACKEND_BASE_URL}/upload/`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }

            const result = await response.json();
            uploadStatus.textContent = `Upload successful: ${result.message}`;
        } catch (error) {
            uploadStatus.textContent = `Upload failed: ${error.message}`;
            console.error('Upload error:', error);
        }
    });

    // --- Query and Display Logic ---
    askButton.addEventListener('click', async () => {
        const query = queryInput.value.trim();

        console.log('1. Value of queryInput.value.trim():', query);

        if (!query) {
            alert("Please enter a question.");
            console.log('2. Query is empty, aborting.');
            return;
        }

        synthesizedAnswerDiv.innerHTML = 'Loading...';
        documentResponsesTableBody.innerHTML = ''; // Clear previous results

        const requestBody = JSON.stringify({ query: query });
        console.log('3. JSON Request Body being sent:', requestBody);
        console.log('4. Type of requestBody:', typeof requestBody);

        try {
            const response = await fetch(`${BACKEND_BASE_URL}/query/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: requestBody
            });

            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }

            const result = await response.json();
            console.log("Query Result:", result);

            // Display Synthesized Answer (Chat Format)
            if (result.answer) {
                let chatContent = `<p><strong>Query:</strong> ${result.original_query}</p>`;
                chatContent += `<p><strong>Answer:</strong> ${result.answer}</p>`;

                if (result.themes && result.themes.length > 0) {
                    chatContent += `<h4>Identified Themes:</h4><ul>`;
                    result.themes.forEach(themeItem => {
                        chatContent += `<li><strong>${themeItem.theme_name}:</strong> `;
                        if (themeItem.theme_description) {
                             chatContent += `${themeItem.theme_description} `;
                        }
                        if (themeItem.citations && themeItem.citations.length > 0) {
                            const docIds = [...new Set(themeItem.citations.map(c => c.document_id))].join(', ');
                            chatContent += `(Documents: ${docIds})`;
                            // Removed the detailed citation list here for conciseness
                            // If you want to display detailed citations elsewhere, you'll need a separate section
                        } else {
                            chatContent += 'No specific citations found for this theme.';
                        }
                        chatContent += `</li>`;
                    });
                    chatContent += `</ul>`;
                }
                synthesizedAnswerDiv.innerHTML = chatContent;
            } else {
                synthesizedAnswerDiv.innerHTML = '<p>No synthesized answer found.</p>';
            }

            // Display Individual Document Responses (Tabular Format)
            if (result.tabular_results && result.tabular_results.length > 0) {
                documentResponsesTableBody.innerHTML = '';
                result.tabular_results.forEach(item => {
                    const row = documentResponsesTableBody.insertRow();
                    row.insertCell().textContent = item["Document ID"];
                    row.insertCell().textContent = item["Extracted Answer"];
                    row.insertCell().textContent = item["Citation"];
                });
            } else {
                const row = documentResponsesTableBody.insertRow();
                const cell = row.insertCell();
                cell.colSpan = 3;
                cell.textContent = 'No individual document responses (tabular format) found.';
            }

        } catch (error) {
            synthesizedAnswerDiv.innerHTML = `<p style="color: red;">Failed to get answer: ${error.message}</p>`;
            documentResponsesTableBody.innerHTML = `<tr><td colspan="3" style="color: red;">Error fetching individual responses.</td></tr>`;
            console.error('Query error:', error);
        }
    });
});