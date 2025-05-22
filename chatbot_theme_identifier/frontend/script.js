document.addEventListener('DOMContentLoaded', () => {
    const documentUpload = document.getElementById('documentUpload');
    const uploadButton = document.getElementById('uploadButton');
    const uploadStatus = document.getElementById('uploadStatus');
    const queryInput = document.getElementById('queryInput');
    const askButton = document.getElementById('askButton');
    const synthesizedAnswerDiv = document.getElementById('synthesizedAnswer');
    const documentResponsesTableBody = document.querySelector('#documentResponsesTable tbody');

    // IMPORTANT: For Vercel deployment, use a relative path for the API endpoint
    // Your Vercel `routes` in vercel.json will handle routing /api requests to your backend
    const BACKEND_BASE_URL = "/api"; 

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
                // Attempt to read error message from response body if available
                const errorData = await response.json().catch(() => ({ message: `HTTP error! Status: ${response.status}` }));
                throw new Error(errorData.detail || errorData.message || `HTTP error! Status: ${response.status}`);
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

        if (!query) {
            alert("Please enter a question.");
            return;
        }

        synthesizedAnswerDiv.innerHTML = 'Loading...';
        documentResponsesTableBody.innerHTML = ''; // Clear previous results

        const requestBody = JSON.stringify({ query: query });

        try {
            const response = await fetch(`${BACKEND_BASE_URL}/query/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: requestBody
            });

            if (!response.ok) {
                 // Attempt to read error message from response body if available
                const errorData = await response.json().catch(() => ({ message: `HTTP error! Status: ${response.status}` }));
                throw new Error(errorData.detail || errorData.message || `HTTP error! Status: ${response.status}`);
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
                            chatContent += `(Documents: ${docIds})`; // Concise display of Document IDs
                            // IMPORTANT: The detailed citation list (with snippets) is intentionally REMOVED here
                            // to keep the themes section clean, as per the desired output format.
                            // If you need detailed citations, consider a separate "Relevant Snippets" section below the main answer.
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
            // This section will only show content if the backend explicitly sends 'tabular_results'
            // which typically happens when the `output_format` in the query request is set to "tabular".
            if (result.tabular_results && result.tabular_results.length > 0) {
                documentResponsesTableBody.innerHTML = ''; // Clear previous table content
                result.tabular_results.forEach(item => {
                    const row = documentResponsesTableBody.insertRow();
                    row.insertCell().textContent = item["Document ID"];
                    row.insertCell().textContent = item["Extracted Answer"];
                    row.insertCell().textContent = item["Citation"];
                });
            } else {
                // Optionally, you can clear the table or show a message if no tabular results are expected/found
                documentResponsesTableBody.innerHTML = `<tr><td colspan="3" class="no-results-message">No individual document responses (tabular format) found for this query type.</td></tr>`;
            }

        } catch (error) {
            synthesizedAnswerDiv.innerHTML = `<p style="color: red;">Failed to get answer: ${error.message}</p>`;
            documentResponsesTableBody.innerHTML = `<tr><td colspan="3" style="color: red;">Error fetching individual responses.</td></tr>`;
            console.error('Query error:', error);
        }
    });
})
