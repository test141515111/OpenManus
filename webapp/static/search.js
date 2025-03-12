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
    const searchResultsContainer = document.getElementById('searchResultsContainer');
    const searchResultsList = document.getElementById('searchResultsList');
    const noResults = document.getElementById('noResults');
    const screenshotsContainer = document.getElementById('screenshotsContainer');
    const screenshotsList = document.getElementById('screenshotsList');
    const noScreenshots = document.getElementById('noScreenshots');
    
    // Initialize Socket.IO if available
    let socket = null;
    try {
        socket = io();
        
        // Socket.IO event handlers
        socket.on('connect', function() {
            console.log('Socket.IO connected');
        });
        
        socket.on('disconnect', function() {
            console.log('Socket.IO disconnected');
        });
        
        socket.on('new_search_report', function(data) {
            updateSearchResults(data);
        });
        
        socket.on('error', function(data) {
            showError(data.message);
        });
        
        console.log('Socket.IO initialized');
    } catch (e) {
        console.error('Socket.IO initialization failed:', e);
        socket = null;
    }
    
    // Form submission handler
    searchForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Get the search parameters
        const query = queryInput.value.trim();
        const numResultsValue = parseInt(numResults.value);
        const languageValue = language.value;
        const includeImagesValue = includeImages.checked;
        
        if (!query) {
            showError('検索クエリを入力してください');
            return;
        }
        
        if (isNaN(numResultsValue) || numResultsValue < 1 || numResultsValue > 5) {
            showError('検索結果の数は1から5の間で指定してください');
            return;
        }
        
        // Disable the submit button
        submitBtn.disabled = true;
        
        // Update UI immediately to show search is being processed
        searchStatus.textContent = '検索中';
        currentQuery.textContent = query;
        searchResultsList.innerHTML = '<div class="alert alert-info">検索中です。しばらくお待ちください...</div>';
        
        // Clear the search results and screenshots
        noResults.style.display = 'none';
        noScreenshots.style.display = 'block';
        screenshotsList.innerHTML = '';
        
        // Submit the search
        submitSearch(query, numResultsValue, languageValue, includeImagesValue);
    });
    
    // Submit search function
    function submitSearch(query, numResultsValue, languageValue, includeImagesValue) {
        // Submit search to API
        fetch('/api/web_search/report', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                query: query,
                num_results: numResultsValue,
                language: languageValue,
                include_images: includeImagesValue
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'error') {
                showError(data.message);
                submitBtn.disabled = false;
                searchStatus.textContent = 'エラー';
            } else {
                // Update the search results
                updateSearchResults({
                    query: query,
                    timestamp: data.timestamp,
                    report: data.report
                });
                
                // Reset the form
                submitBtn.disabled = false;
                searchStatus.textContent = '完了';
            }
        })
        .catch(error => {
            showError('検索の実行中にエラーが発生しました: ' + error.message);
            submitBtn.disabled = false;
            searchStatus.textContent = 'エラー';
        });
    }
    
    // Update search results function
    function updateSearchResults(data) {
        if (data.report) {
            noResults.style.display = 'none';
            searchResultsList.innerHTML = formatReport(data.report);
            
            // Update screenshots if available
            if (data.report.screenshots && data.report.screenshots.length > 0) {
                noScreenshots.style.display = 'none';
                screenshotsList.innerHTML = '';
                
                data.report.screenshots.forEach(function(screenshot) {
                    const img = document.createElement('img');
                    img.src = screenshot;
                    img.alt = '検索スクリーンショット';
                    img.className = 'img-fluid mb-3';
                    screenshotsList.appendChild(img);
                });
            } else {
                noScreenshots.style.display = 'block';
                screenshotsList.innerHTML = '';
            }
        } else {
            noResults.style.display = 'block';
            searchResultsList.innerHTML = '';
            noScreenshots.style.display = 'block';
            screenshotsList.innerHTML = '';
        }
        
        // Enable the submit button
        submitBtn.disabled = false;
    }
    
    // Format report function
    function formatReport(report) {
        let html = '';
        
        if (report.summary) {
            html += '<div class="mb-4"><h3 class="h6">検索サマリー</h3><p>' + report.summary + '</p></div>';
        }
        
        if (report.results && report.results.length > 0) {
            html += '<div class="mb-4"><h3 class="h6">検索結果</h3><ul class="list-group">';
            
            report.results.forEach(function(result, index) {
                html += '<li class="list-group-item">';
                html += '<h4 class="h6">' + (index + 1) + '. ' + (result.title || '無題') + '</h4>';
                
                if (result.url) {
                    html += '<p><a href="' + result.url + '" target="_blank">' + result.url + '</a></p>';
                }
                
                if (result.snippet) {
                    html += '<p>' + result.snippet + '</p>';
                }
                
                html += '</li>';
            });
            
            html += '</ul></div>';
        }
        
        return html;
    }
    
    // Show error function
    function showError(message) {
        alert('エラー: ' + message);
        console.error('Error:', message);
        
        // Update UI to show error state
        if (searchStatus) {
            searchStatus.textContent = 'エラー';
        }
        
        // Display error in results area
        if (searchResultsList) {
            searchResultsList.innerHTML = '<div class="alert alert-danger">エラー: ' + message + '</div>';
            noResults.style.display = 'none';
        }
    }
});
