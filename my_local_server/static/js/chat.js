class AccountingChat {
    constructor() {
        this.conversationHistory = [];
        this.initializeChat();
    }

    initializeChat() {
        // Get schema on initialization
        this.getSchema().then(schema => {
            if (schema) {
                document.getElementById('schema-content').textContent = 
                    JSON.stringify(schema, null, 2);
            }
        });

        // Initialize event listeners
        const chatForm = document.getElementById('chat-form');
        const modeSelect = document.getElementById('chat-mode');
        
        if (chatForm) {
            chatForm.addEventListener('submit', this.handleSubmit.bind(this));
        }
        
        if (modeSelect) {
            modeSelect.addEventListener('change', () => {
                const schemaInfo = document.getElementById('schema-info');
                if (modeSelect.value === 'accounting') {
                    schemaInfo.classList.remove('collapse');
                } else {
                    schemaInfo.classList.add('collapse');
                }
            });
        }
    }

    async sendMessage(message) {
        try {
            const response = await fetch('/api/chat/accounting', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    history: this.conversationHistory
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            
            // Add messages to history
            this.conversationHistory.push(
                { role: 'user', content: message },
                { role: 'assistant', content: data.message }
            );

            // Format response with any query results
            let formattedResponse = data.message;
            if (data.data) {
                formattedResponse += '\n\nQuery Results:\n' + 
                    JSON.stringify(data.data, null, 2);
            }

            return formattedResponse;

        } catch (error) {
            console.error('Error:', error);
            return 'Error processing your request. Please try again.';
        }
    }

    async getSchema() {
        try {
            const response = await fetch('/api/accounting/schema');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            return data.schema;
        } catch (error) {
            console.error('Error getting schema:', error);
            return null;
        }
    }

    async handleSubmit(event) {
        event.preventDefault();
        const messageInput = document.getElementById('message-input');
        const message = messageInput.value.trim();
        
        if (message) {
            // Add user message to chat
            this.appendMessage('user', message);
            messageInput.value = '';

            // Get response from server
            const response = await this.sendMessage(message);

            // Add assistant response to chat
            this.appendMessage('assistant', response);
        }
    }

    appendMessage(role, content) {
        const chatMessages = document.getElementById('chat-messages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${role}-message`;
        
        // Parse and format the content
        const formattedContent = this._parseContent(content);
        
        messageDiv.innerHTML = `
            <div class="message-header">${role === 'user' ? 'You' : 'Assistant'}</div>
            <div class="message-content">${formattedContent}</div>
        `;
        
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    _parseContent(content) {
        let formattedContent = '';
        
        // Extract thinking process if present
        // Look for text before the first SQL block or explanation
        const beforeSql = content.split(/```sql|### Explanation/)[0];
        if (beforeSql.trim()) {
            formattedContent += `
                <div class="thinking-process">
                    <button class="btn btn-sm btn-outline-secondary mb-2" 
                            onclick="this.nextElementSibling.classList.toggle('show')">
                        Show Thinking Process
                    </button>
                    <div class="collapse thinking-content">
                        <div class="card card-body bg-light mb-3">
                            ${this._formatMessage(beforeSql)}
                        </div>
                    </div>
                </div>
            `;
        }
        
        // Extract SQL query if present
        const sqlMatch = content.match(/```sql\n([\s\S]*?)```/);
        if (sqlMatch) {
            const sqlQuery = sqlMatch[1].trim();
            formattedContent += `
                <div class="sql-section mb-3">
                    <div class="sql-header">
                        <span class="badge bg-secondary">SQL Query</span>
                    </div>
                    <div class="sql-content">
                        <pre><code class="language-sql">${this._highlightSql(sqlQuery)}</code></pre>
                    </div>
                </div>
            `;
        }
        
        // Get content after SQL but before explanation
        if (sqlMatch) {
            const afterSql = content.split('```')[2];
            if (afterSql) {
                const resultContent = afterSql.split('### Explanation')[0].trim();
                if (resultContent) {
                    formattedContent += `
                        <div class="actual-response">
                            ${this._formatMessage(resultContent)}
                        </div>
                    `;
                }
            }
        }
        
        return formattedContent || this._formatMessage(content);
    }

    _highlightSql(sql) {
        return sql.replace(/\b(SELECT|FROM|WHERE|GROUP BY|ORDER BY|JOIN|ON|AS|AND|OR|IN|LIKE|BETWEEN|IS|NULL|NOT|DISTINCT|COUNT|SUM|AVG|MIN|MAX)\b/gi, 
            '<span class="sql-keyword">$1</span>');
    }

    _formatMessage(content) {
        // Enhanced markdown-like formatting
        return content
            .replace(/\n/g, '<br>')
            // Code blocks with language
            .replace(/```(\w+)?\n([\s\S]*?)```/g, (_, lang, code) => `
                <pre><code class="language-${lang || 'plaintext'}">${code.trim()}</code></pre>
            `)
            // Inline code
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            // SQL keywords highlighting
            .replace(/\b(SELECT|FROM|WHERE|GROUP BY|ORDER BY|JOIN|ON|AS|AND|OR|IN|LIKE|BETWEEN|IS|NULL|NOT|DISTINCT|COUNT|SUM|AVG|MIN|MAX)\b/gi, 
                    '<span class="sql-keyword">$1</span>');
    }
}

// Initialize the chat when the document is ready
document.addEventListener('DOMContentLoaded', () => {
    window.accountingChat = new AccountingChat();
}); 