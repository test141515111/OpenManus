// Main script for OpenManus Web Search UI
document.addEventListener('DOMContentLoaded', function() {
    // DOM elements
    const searchForm = document.getElementById('searchForm');
    const queryInput = document.getElementById('queryInput');
    const numResults = document.getElementById('numResults');
    const language = document.getElementById('language');
    const includeImages = document.getElementById('includeImages');
    const submitBtn = document.getElementById('submitBtn');
    const searchStatus = document.getElementById('searchStatus');
    const currentQuery = document.getElementById('currentQuery');
    const searchResultsList = document.getElementById('searchResultsList');
    const screenshotsList = document.getElementById('screenshotsList');
    const noResults = document.getElementById('noResults');
    const noScreenshots = document.getElementById('noScreenshots');
    
    // Initialize Socket.IO
    let socket = null;
    try {
        socket = io();
        
        // Socket.IO event handlers
        socket.on('connect', function() {
            console.log('Connected to server via Socket.IO');
        });
        
        socket.on('disconnect', function() {
            console.log('Disconnected from server');
        });
        
        socket.on('new_search_report', function(data) {
            console.log('New search report received:', data);
            displaySearchReport(data);
        });
        
        socket.on('web_search_error', function(data) {
            console.log('Search error received:', data);
            displaySearchError(data);
        });
    } catch (e) {
        console.log('Socket.IO not available, falling back to HTTP API');
        socket = null;
    }
    
    // Submit search form
    searchForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const query = queryInput.value.trim();
        if (!query) {
            alert('検索クエリを入力してください');
            return;
        }
        
        // Validate number of results
        const numResultsValue = parseInt(numResults.value);
        if (isNaN(numResultsValue) || numResultsValue < 1 || numResultsValue > 5) {
            alert('結果の数は1から5の間で指定してください');
            return;
        }
        
        // Disable form while search is running
        submitBtn.disabled = true;
        submitBtn.innerHTML = '検索中... <span class="loading"></span>';
        
        // Update UI immediately
        searchStatus.textContent = '検索中';
        searchStatus.className = 'status-running';
        currentQuery.textContent = query;
        
        // Clear previous results
        searchResultsList.innerHTML = '';
        screenshotsList.innerHTML = '';
        noResults.style.display = 'block';
        noScreenshots.style.display = 'block';
        
        // Prepare search parameters
        const searchParams = {
            query: query,
            num_results: numResultsValue,
            language: language.value,
            include_images: includeImages.checked
        };
        
        // Submit search via HTTP API directly for more reliable results
        submitViaHttp(searchParams);
        
        // Display immediate feedback
        searchStatus.textContent = '検索中';
        searchStatus.className = 'status-running';
        currentQuery.textContent = query;
        
        // Log the search attempt
        console.log('Search submitted via HTTP API:', searchParams);
        
        // Function to submit via HTTP API
        function submitViaHttp(params) {
            fetch('/api/web_search/report', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(params)
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Search submitted successfully
                    console.log('Search submitted successfully via HTTP');
                    displaySearchReport(data);
                } else {
                    console.error('API error:', data.message);
                    displaySearchError({message: data.message || 'タスクの送信中にエラーが発生しました'});
                }
            })
            .catch(error => {
                console.error('Fetch error:', error);
                displaySearchError({message: 'タスクの送信中にエラーが発生しました'});
                resetForm();
            });
        }
    });
    
    // Display search report
    function displaySearchReport(data) {
        // Update status
        searchStatus.textContent = '完了';
        searchStatus.className = 'status-completed';
        
        // Update current query
        if (data.query) {
            currentQuery.textContent = data.query;
        }
        
        // Reset form
        resetForm();
        
        // Display search results
        if (data.report) {
            displayResults(data.report);
        } else {
            noResults.style.display = 'block';
            searchResultsList.innerHTML = '';
        }
    }
    
    // Display search error
    function displaySearchError(data) {
        // Update status
        searchStatus.textContent = '失敗';
        searchStatus.className = 'status-failed';
        
        // Reset form
        resetForm();
        
        // Display error message
        noResults.style.display = 'none';
        searchResultsList.innerHTML = '<div class="alert alert-danger">' + (data.message || 'タスクの送信中にエラーが発生しました') + '</div>';
        
        // Log error to console
        console.error('Search error:', data);
    }
    
    // Display search results
    function displayResults(report) {
        noResults.style.display = 'none';
        searchResultsList.innerHTML = '';
        
        // Display search screenshot if available
        if (report.search_screenshot) {
            noScreenshots.style.display = 'none';
            
            const screenshotItem = document.createElement('div');
            screenshotItem.className = 'screenshot-item';
            
            const timestamp = document.createElement('div');
            timestamp.className = 'timestamp';
            timestamp.textContent = report.timestamp || '検索結果';
            
            const img = document.createElement('img');
            img.src = 'data:image/png;base64,' + report.search_screenshot;
            img.alt = '検索結果のスクリーンショット';
            img.className = 'screenshot-img';
            
            screenshotItem.appendChild(timestamp);
            screenshotItem.appendChild(img);
            
            screenshotsList.appendChild(screenshotItem);
        }
        
        // Create results container
        const resultsContainer = document.createElement('div');
        resultsContainer.className = 'search-results';
        
        // Add search metadata
        const metaInfo = document.createElement('div');
        metaInfo.className = 'search-meta';
        metaInfo.innerHTML = `
            <p><strong>検索クエリ:</strong> ${report.query}</p>
            <p><strong>検索時間:</strong> ${report.timestamp}</p>
            <p><strong>結果数:</strong> ${report.num_results}</p>
        `;
        resultsContainer.appendChild(metaInfo);
        
        // Add individual results
        if (report.results && report.results.length > 0) {
            report.results.forEach((result, index) => {
                const resultItem = document.createElement('div');
                resultItem.className = 'search-result-item';
                
                // Result header
                const resultHeader = document.createElement('div');
                resultHeader.className = 'result-header';
                resultHeader.innerHTML = `
                    <h3 class="result-title">${index + 1}. ${result.title || '無題'}</h3>
                    <a href="${result.url}" target="_blank" class="result-url">${result.url}</a>
                `;
                resultItem.appendChild(resultHeader);
                
                // Result snippet
                if (result.snippet) {
                    const snippet = document.createElement('div');
                    snippet.className = 'result-snippet';
                    snippet.textContent = result.snippet;
                    resultItem.appendChild(snippet);
                }
                
                // Result content
                if (result.content) {
                    const content = document.createElement('div');
                    content.className = 'result-content';
                    content.textContent = result.content;
                    resultItem.appendChild(content);
                }
                
                // Result screenshot
                if (result.screenshot) {
                    const screenshotContainer = document.createElement('div');
                    screenshotContainer.className = 'result-screenshot';
                    
                    const img = document.createElement('img');
                    img.src = 'data:image/png;base64,' + result.screenshot;
                    img.alt = result.title || 'ページのスクリーンショット';
                    img.className = 'result-img';
                    
                    screenshotContainer.appendChild(img);
                    resultItem.appendChild(screenshotContainer);
                }
                
                // Result error if any
                if (result.error) {
                    const error = document.createElement('div');
                    error.className = 'result-error';
                    error.textContent = result.error;
                    resultItem.appendChild(error);
                }
                
                resultsContainer.appendChild(resultItem);
            });
        } else {
            const noResultsMsg = document.createElement('div');
            noResultsMsg.className = 'no-results-message';
            noResultsMsg.textContent = '検索結果が見つかりませんでした。';
            resultsContainer.appendChild(noResultsMsg);
        }
        
        searchResultsList.appendChild(resultsContainer);
    }
    
    // Reset form after search completion
    function resetForm() {
        submitBtn.disabled = false;
        submitBtn.innerHTML = '検索を実行';
    }
});
