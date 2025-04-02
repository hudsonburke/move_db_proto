// Enable Vue debugging
Vue.config.devtools = true;
Vue.config.debug = true;
Vue.config.performance = true;

document.addEventListener('DOMContentLoaded', function() {
    console.log("[Debug] DOMContentLoaded event fired. Initializing Vue...");
    // Create Vue instance with proper configuration ONLY after DOM is ready
    const app = new Vue({
        el: '#app',
        delimiters: ['{{', '}}'],  // Explicitly set template delimiters
        data: {
            directoryPath: '',
            directoryStatus: '',
            searchFilters: {
                filename: { value: '', use_regex: false },
                classification: { value: '', use_regex: false },
                subject: { value: '', use_regex: false },
                session_name: { value: '', use_regex: false },
                min_duration: null,
                max_duration: null,
                min_frame_count: null,
                max_frame_count: null,
                marker: { value: '', use_regex: false },
                channel: { value: '', use_regex: false },
                event: { value: '', use_regex: false },
                analysis_name: '',
                analysis_params: '{}'
            },
            classifications: [],
            subjects: [],
            sessions: [],
            analyses: [],
            selectedAnalysis: null,
            selectedClassification: '',
            selectedSubject: '',
            selectedSession: '',
            files: [],
            fileTree: {},
            fileCountInfo: '',
            loading: false,
            filterGroups: {
                basic: true,
                content: true,
                analysis: false
            },
            
            // --- Group Management Data ---
            groups: [], // Holds the list of groups
            loadingGroups: false,
            selectedFiles: [], // Array of selected file IDs
            selectAllFiles: false, // State for the "select all" checkbox
            selectedGroupId: null, // ID of the group selected in the 'Add to Group' modal
            newGroup: { // Holds data for the create/edit group form
                name: '',
                description: ''
            },
            editingGroupId: null, // ID of the group being edited, null if creating new
            currentGroup: null, // Holds the group whose files are being viewed
            groupFiles: [], // Holds the files for the currently viewed group
            loadingGroupFiles: false,
            savingGroup: false, // Loading state for create/edit group action
            addingFilesToGroup: false, // Loading state for adding files to group action

            // --- Plotting Data ---
            availablePlots: [],
            selectedPlot: null,
            selectedPlotDetails: null,
            isPlotLoading: false,
            plotMarkerOptions: [], // Separate options for selectors
            plotChannelOptions: [], // Separate options for selectors
            selectedFileId: null, // ID of the file selected in the plot tab
        },
        computed: {
            parsedAnalysisParams: {
                get() {
                    try {
                        return JSON.parse(this.searchFilters.analysis_params);
                    } catch (e) {
                        return {};
                    }
                },
                set(value) {
                    this.searchFilters.analysis_params = JSON.stringify(value);
                }
            },
            // Computed property to show/hide marker selector based on selected plot
            showMarkerSelector() {
                return this.selectedPlotDetails && this.selectedPlotDetails.requires_markers;
            },
            // Computed property to show/hide channel selector based on selected plot
            showChannelSelector() {
                return this.selectedPlotDetails && this.selectedPlotDetails.requires_channels;
            }
        },
        methods: {
            initializeComponents() {
                console.log("[Debug] Initializing Bootstrap components...");
                // Initialize Bootstrap modals
                try {
                    this.fileDetailsModal = new bootstrap.Modal(document.getElementById('fileDetailsModal'));
                    this.addToGroupModal = new bootstrap.Modal(document.getElementById('addToGroupModal'));
                    this.createGroupModal = new bootstrap.Modal(document.getElementById('createGroupModal'));
                    this.groupFilesModal = new bootstrap.Modal(document.getElementById('groupFilesModal'));
                    console.log("[Debug] Bootstrap modals initialized successfully.");
                } catch (error) {
                    console.error("[Debug] Error initializing Bootstrap modals:", error);
                }

                 // Reset forms when modals are hidden
                document.getElementById('createGroupModal').addEventListener('hidden.bs.modal', () => {
                    this.editingGroupId = null;
                    this.newGroup = { name: '', description: '' };
                    this.savingGroup = false; // Reset loading state
                });
                 document.getElementById('addToGroupModal').addEventListener('hidden.bs.modal', () => {
                    this.selectedGroupId = null;
                    this.addingFilesToGroup = false; // Reset loading state
                });
                 document.getElementById('groupFilesModal').addEventListener('hidden.bs.modal', () => {
                    this.currentGroup = null;
                    this.groupFiles = [];
                });
            },
            handleDirectoryScan() {
                if (!this.directoryPath) {
                    this.directoryStatus = '<div class="alert alert-warning">Please enter a directory path</div>';
                    return;
                }
                this.directoryStatus = '<div class="d-flex align-items-center"><div class="spinner-border spinner-border-sm me-2" role="status"></div>Scanning directory (this will run in the background)...</div>';
                fetch(`/api/directory-scan`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ root_directory: this.directoryPath })
                })
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP error! Status: ${response.status}`);
                    }
                    return response.json();
                })
                .then(data => {
                    // For background tasks, show a success message that the scan has started
                    if (data.status === "processing") {
                        this.directoryStatus = '<div class="alert alert-info">' + data.detail + 
                            ' <br><small>Files will appear in searches once processing is complete.</small></div>';
                        
                        // Set a timer to refresh the classifications after a delay to allow for processing
                        setTimeout(() => {
                            this.loadClassifications();
                            this.searchFiles();
                        }, 5000); // Try checking after 5 seconds
                    } else {
                        // Handle case when old API endpoint is still being used
                        this.directoryStatus = `<div class="alert alert-success">Successfully indexed ${data.indexed?.length || 0} files</div>`;
                        this.loadClassifications();
                        this.searchFiles();
                    }
                    
                    this.selectedClassification = '';
                    this.selectedSubject = '';
                    this.selectedSession = '';
                })
                .catch(error => {
                    this.directoryStatus = `<div class="alert alert-danger">Directory scanning failed: ${error.message}</div>`;
                });
            },
            loadClassifications() {
                fetch(`/api/classifications/`)
                .then(response => response.json())
                .then(data => {
                    this.classifications = data.classifications;
                })
                .catch(error => {
                    console.error("Error loading classifications:", error);
                });
            },
            loadSubjects() {
                fetch(`/api/subjects/?classification=${encodeURIComponent(this.selectedClassification)}`)
                .then(response => response.json())
                .then(data => {
                    this.subjects = data.subjects;
                    this.selectedSubject = '';
                    this.selectedSession = '';
                    this.sessions = [];
                    this.searchFiles();
                })
                .catch(error => {
                    console.error("Error loading subjects:", error);
                });
            },
            loadSessions() {
                fetch(`/api/sessions/?classification=${encodeURIComponent(this.selectedClassification)}&subject=${encodeURIComponent(this.selectedSubject)}`)
                .then(response => response.json())
                .then(data => {
                    this.sessions = data.sessions;
                    this.selectedSession = '';
                    this.searchFiles();
                })
                .catch(error => {
                    console.error("Error loading sessions:", error);
                });
            },
            loadAnalyses() {
                fetch(`/api/analyses/`)
                    .then(response => response.json())
                    .then(data => {
                        this.analyses = data.analyses;
                    })
                    .catch(error => {
                        console.error("Error loading analyses:", error);
                    });
            },
            onAnalysisChange() {
                if (this.searchFilters.analysis_name) {
                    const selectedAnalysis = this.analyses.find(a => a.name === this.searchFilters.analysis_name);
                    if (selectedAnalysis) {
                        this.selectedAnalysis = selectedAnalysis;
                        
                        // Initialize default parameter values
                        const defaultParams = {};
                        for (const [key, type] of Object.entries(selectedAnalysis.parameters)) {
                            if (type === 'int' || type === int) {
                                defaultParams[key] = 0;
                            } else if (type === 'float' || type === float) {
                                defaultParams[key] = 0.0;
                            } else if (type === 'str' || type === String || type === str) {
                                defaultParams[key] = '';
                            } else if (type === 'bool' || type === bool) {
                                defaultParams[key] = false;
                            }
                        }
                        this.parsedAnalysisParams = defaultParams;
                    }
                } else {
                    this.selectedAnalysis = null;
                    this.parsedAnalysisParams = {};
                }
            },
            updateAnalysisParam(key, value) {
                const params = this.parsedAnalysisParams;
                params[key] = value;
                this.parsedAnalysisParams = params;
            },
            buildFileTree(files) {
                // Create tree structure
                const tree = {};
                
                files.forEach(file => {
                    const classification = file.classification || 'Uncategorized';
                    const subject = file.subject_name || 'Unknown';
                    const session = file.session_name || 'Default';
                    
                    // Initialize structure if needed
                    if (!tree[classification]) {
                        tree[classification] = { subjects: {} };
                    }
                    
                    if (!tree[classification].subjects[subject]) {
                        tree[classification].subjects[subject] = { sessions: {} };
                    }
                    
                    if (!tree[classification].subjects[subject].sessions[session]) {
                        tree[classification].subjects[subject].sessions[session] = { files: [] };
                    }
                    
                    // Add file to the appropriate place in the tree
                    tree[classification].subjects[subject].sessions[session].files.push(file);
                });
                
                return tree;
            },
            toggleRegex(field) {
                if (this.searchFilters[field]) {
                    this.searchFilters[field].use_regex = !this.searchFilters[field].use_regex;
                }
            },
            searchFiles() {
                this.loading = true;
                const params = new URLSearchParams();
                
                // Add basic metadata filters with individual regex flags
                if (this.searchFilters.filename.value) {
                    params.append('filename', this.searchFilters.filename.value);
                    if (this.searchFilters.filename.use_regex) {
                        params.append('filename_regex', 'true');
                    }
                }
                
                if (this.searchFilters.classification.value || this.selectedClassification) {
                    params.append('classification', this.searchFilters.classification.value || this.selectedClassification);
                    if (this.searchFilters.classification.use_regex && !this.selectedClassification) {
                        params.append('classification_regex', 'true');
                    }
                }
                
                if (this.searchFilters.subject.value || this.selectedSubject) {
                    params.append('subject', this.searchFilters.subject.value || this.selectedSubject);
                    if (this.searchFilters.subject.use_regex && !this.selectedSubject) {
                        params.append('subject_regex', 'true');
                    }
                }
                
                if (this.searchFilters.session_name.value || this.selectedSession) {
                    params.append('session_name', this.searchFilters.session_name.value || this.selectedSession);
                    if (this.searchFilters.session_name.use_regex && !this.selectedSession) {
                        params.append('session_regex', 'true');
                    }
                }
                
                // Add numeric range filters
                if (this.searchFilters.min_duration !== null) params.append('min_duration', this.searchFilters.min_duration);
                if (this.searchFilters.max_duration !== null) params.append('max_duration', this.searchFilters.max_duration);
                if (this.searchFilters.min_frame_count !== null) params.append('min_frame_count', this.searchFilters.min_frame_count);
                if (this.searchFilters.max_frame_count !== null) params.append('max_frame_count', this.searchFilters.max_frame_count);
                
                // Add content filters with individual regex flags
                if (this.searchFilters.marker.value) {
                    params.append('marker', this.searchFilters.marker.value);
                    if (this.searchFilters.marker.use_regex) {
                        params.append('marker_regex', 'true');
                    }
                }
                
                if (this.searchFilters.channel.value) {
                    params.append('channel', this.searchFilters.channel.value);
                    if (this.searchFilters.channel.use_regex) {
                        params.append('channel_regex', 'true');
                    }
                }
                
                if (this.searchFilters.event.value) {
                    params.append('event', this.searchFilters.event.value);
                    if (this.searchFilters.event.use_regex) {
                        params.append('event_regex', 'true');
                    }
                }
                
                // Add analysis filters
                if (this.searchFilters.analysis_name) {
                    params.append('analysis_name', this.searchFilters.analysis_name);
                    
                    // Only pass params if valid JSON
                    try {
                        const analysisParams = JSON.parse(this.searchFilters.analysis_params);
                        if (analysisParams && typeof analysisParams === 'object') {
                            params.append('analysis_params', this.searchFilters.analysis_params);
                        }
                    } catch (e) {
                        console.error("Invalid analysis parameters JSON:", e);
                    }
                }
                
                params.append('limit', 10000);
                
                console.log('Fetching files with params:', params.toString());
                fetch(`/api/files/?${params.toString()}`)
                    .then(response => {
                        if (!response.ok) {
                            throw new Error(`HTTP error! Status: ${response.status}`);
                        }
                        return response.json();
                    })
                    .then(data => {
                        console.log('Received data:', data);  // Debug log
                        this.files = data.files || [];
                        console.log('Set files array:', this.files);  // Debug log
                        this.fileTree = this.buildFileTree(this.files);
                        this.fileCountInfo = `Total: ${data.pagination?.filtered || 0} of ${data.pagination?.total || 0} files`;
                        console.log('Files loaded:', this.files.length);
                    })
                    .catch(error => {
                        console.error(`Error loading files: ${error.message}`);
                        this.fileTree = {};
                        this.files = [];
                        this.fileCountInfo = "Error loading files";
                    })
                    .finally(() => {
                        this.loading = false;
                    });
            },
            clearSearchForm() {
                this.searchFilters = {
                    filename: { value: '', use_regex: false },
                    classification: { value: '', use_regex: false },
                    subject: { value: '', use_regex: false },
                    session_name: { value: '', use_regex: false },
                    min_duration: null,
                    max_duration: null,
                    min_frame_count: null,
                    max_frame_count: null,
                    marker: { value: '', use_regex: false },
                    channel: { value: '', use_regex: false },
                    event: { value: '', use_regex: false },
                    analysis_name: '',
                    analysis_params: '{}'
                };
                this.selectedAnalysis = null;
                this.selectedClassification = '';
                this.selectedSubject = '';
                this.selectedSession = '';
                this.loadClassifications();
                this.searchFiles();
            },
            toggleFilterGroup(groupName) {
                // Fix for collapsible filters
                Vue.set(this.filterGroups, groupName, !this.filterGroups[groupName]);
            },
            showFileDetails(fileId) {
                const modalTitle = document.getElementById('fileDetailsTitle');
                const modalBody = document.getElementById('fileDetailsBody');
                const downloadBtn = document.getElementById('downloadFileBtn');
                modalTitle.innerText = 'Loading...';
                modalBody.innerHTML = `
                    <div class="text-center">
                        <div class="spinner-border" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                    </div>
                `;
                downloadBtn.style.display = 'none';
                
                this.fileDetailsModal.show();
                fetch(`/api/files/${fileId}`)
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP error! Status: ${response.status}`);
                    }
                    return response.json();
                })
                .then(file => {
                    modalTitle.innerText = file.filename;
                    const markerBadges = file.markers.map(m => 
                        `<span class="badge bg-secondary marker-badge">${m.marker_name}</span>`
                    ).join('');
                    const channelBadges = file.channels.map(c => 
                        `<span class="badge bg-info channel-badge">${c.channel_name}</span>`
                    ).join('');
                    const eventBadges = file.events.map(e => 
                        `<span class="badge bg-warning event-badge">${e.event_name} (${e.event_time !== undefined ? e.event_time.toFixed(2) : '0.00'}s)</span>`
                    ).join('');
                    const classification = file.classification || 'Uncategorized';
                    const subject = file.subject_name || 'Unknown';
                    const session = file.session_name || 'Default';
                    const hierarchyPath = `
                        <div class="tree-path">
                            <i class="bi bi-diagram-3"></i> 
                            <strong>${classification}</strong> / 
                            <strong>${subject}</strong> / 
                            <strong>${session}</strong> / 
                            ${file.filename}
                        </div>
                    `;
                    modalBody.innerHTML = `
                        ${hierarchyPath}
                        <div class="row">
                            <div class="col-md-6">
                                <p><strong>Classification:</strong> ${classification}</p>
                                <p><strong>Subject:</strong> ${subject}</p>
                                <p><strong>Session:</strong> ${session}</p>
                                <p><strong>Duration:</strong> ${file.duration !== undefined ? file.duration.toFixed(2) : '0.00'}s</p>
                                <p><strong>Frames:</strong> ${file.frame_count}</p>
                            </div>
                            <div class="col-md-6">
                                <p><strong>Sample Rate:</strong> ${file.sample_rate !== undefined ? file.sample_rate.toFixed(2) : '0.00'} Hz</p>
                                <p><strong>File Size:</strong> ${this.formatFileSize(file.file_size)}</p>
                                <p><strong>Date Added:</strong> ${new Date(file.date_added).toLocaleString()}</p>
                                <p><strong>Path:</strong> <span class="text-truncate d-block">${file.filepath}</span></p>
                            </div>
                        </div>
                        <div class="mt-4">
                            <h6>Markers (${file.markers.length}):</h6>
                            <div>${markerBadges || 'No markers'}</div>
                        </div>
                        <div class="mt-3">
                            <h6>Analog Channels (${file.channels.length}):</h6>
                            <div>${channelBadges || 'No channels'}</div>
                        </div>
                        <div class="mt-3">
                            <h6>Events (${file.events.length}):</h6>
                            <div>${eventBadges || 'No events'}</div>
                        </div>
                    `;
                    downloadBtn.style.display = 'block';
                    downloadBtn.href = `/api/files/${fileId}/download`;
                })
                .catch(error => {
                    modalBody.innerHTML = `<div class="alert alert-danger">Error loading file details: ${error.message}</div>`;
                });
            },
            deleteFile(fileId) {
                if (!confirm('Are you sure you want to delete this file? This action cannot be undone.')) {
                    return;
                }
                fetch(`/api/files/${fileId}`, {
                    method: 'DELETE'
                })
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP error! Status: ${response.status}`);
                    }
                    return response.json();
                })
                .then(data => {
                    this.showNotification('File deleted successfully');
                    this.searchFiles();
                })
                .catch(error => {
                    alert(`Error deleting file: ${error.message}`);
                });
            },
            formatFileSize(bytes) {
                if (bytes === 0) return '0 Bytes';
                const k = 1024;
                const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
                const i = Math.floor(Math.log(bytes) / Math.log(k));
                return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
            },
            showNotification(message, type = 'success') {
                // Create a Bootstrap alert
                const alertDiv = document.createElement('div');
                alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
                alertDiv.role = 'alert';
                alertDiv.innerHTML = `
                    ${message}
                    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                `;
                
                // Add to the top of the container
                const container = document.querySelector('.container');
                container.insertBefore(alertDiv, container.firstChild);
                
                // Auto-remove after 5 seconds
                setTimeout(() => {
                    alertDiv.remove();
                }, 5000);
            },
            
            // --- Helper Methods ---
            formatDate(dateString) {
                if (!dateString) return 'N/A';
                try {
                    return new Date(dateString).toLocaleDateString(undefined, {
                        year: 'numeric', month: 'short', day: 'numeric'
                    });
                } catch (e) {
                    return dateString; // Return original if formatting fails
                }
            },
            formatDuration(seconds) {
                if (seconds === null || seconds === undefined || isNaN(seconds)) return 'N/A';
                return seconds.toFixed(2) + 's';
            },
            
            // --- File Selection Methods ---
            toggleSelectFile(fileId) {
                const index = this.selectedFiles.indexOf(fileId);
                if (index === -1) {
                    this.selectedFiles.push(fileId);
                } else {
                    this.selectedFiles.splice(index, 1);
                }

                // Uncheck "select all" if any file is deselected manually
                if (index !== -1 && this.selectAllFiles) {
                    this.selectAllFiles = false;
                }
                // Check "select all" if all files are now selected
                else if (index === -1 && this.selectedFiles.length === this.files.length && this.files.length > 0) {
                     this.selectAllFiles = true;
                }
            },
            toggleSelectAll() {
                if (this.selectAllFiles) {
                    // Select all currently displayed files
                    this.selectedFiles = this.files.map(file => file.id);
                } else {
                    // Deselect all files
                    this.selectedFiles = [];
                }
            },
            clearSelection() {
                this.selectedFiles = [];
                this.selectAllFiles = false;
            },

            // --- Group Management Methods ---
            async loadGroups() {
                this.loadingGroups = true;
                try {
                    const response = await fetch('/api/groups/');
                    if (!response.ok) {
                        throw new Error(`HTTP error! Status: ${response.status}`);
                    }
                    this.groups = await response.json();
                } catch (error) {
                    console.error("Error loading groups:", error);
                    this.showNotification(`Error loading groups: ${error.message}`, 'danger');
                } finally {
                    this.loadingGroups = false;
                }
            },

            showAddToGroupModal() {
                if (this.selectedFiles.length === 0) {
                    this.showNotification('Please select at least one file first.', 'warning');
                    return;
                }
                // Ensure groups are loaded before showing modal
                this.loadGroups().then(() => {
                    this.selectedGroupId = null; // Reset selection
                    this.addToGroupModal.show();
                });
            },

            async addSelectedFilesToGroup() {
                if (!this.selectedGroupId || this.selectedFiles.length === 0) {
                    this.showNotification('Please select a group and at least one file.', 'warning');
                    return;
                }
                this.addingFilesToGroup = true;

                const requestBodyString = JSON.stringify(this.selectedFiles);

                try {
                    const response = await fetch(`/api/groups/${this.selectedGroupId}/files`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: requestBodyString // Use the stringified variable
                    });
                    const result = await response.json(); // Read response body even for non-200s
                    if (!response.ok) {
                        throw new Error(result.detail || `HTTP error! Status: ${response.status}`);
                    }
                    this.addToGroupModal.hide();
                    this.showNotification(result.detail || `Successfully added files.`, 'success');
                    this.clearSelection();
                    await this.loadGroups(); // Refresh group list to show updated counts
                } catch (error) {
                    console.error("Error adding files to group:", error);
                    this.showNotification(`Error adding files: ${error.message}`, 'danger');
                } finally {
                    this.addingFilesToGroup = false;
                }
            },

            showCreateGroupModal() {
                this.editingGroupId = null;
                this.newGroup = { name: '', description: '' };
                // Wait for Vue to update the DOM based on editingGroupId being null
                this.$nextTick(() => {
                    try {
                         this.createGroupModal.show();
                         console.log("[Debug] createGroupModal.show() called successfully.");
                    } catch (e) {
                        console.error("[Debug] Error calling createGroupModal.show():", e);
                    }
                });
            },

            showEditGroupModal(group) {
                 console.log(`[Debug] showEditGroupModal called for group: ${group.id}`);
                this.editingGroupId = group.id;
                this.newGroup = { name: group.name, description: group.description };
                // Wait for Vue to update the DOM based on editingGroupId having a value
                 this.$nextTick(() => {
                    console.log("[Debug] $nextTick callback: Attempting to show createGroupModal for editing");
                     try {
                        this.createGroupModal.show();
                        console.log("[Debug] createGroupModal.show() for editing called successfully.");
                     } catch (e) {
                        console.error("[Debug] Error calling createGroupModal.show() for editing:", e);
                     }
                });
            },

            async saveGroup() {
                console.log("[Debug] saveGroup method called.");
                if (!this.newGroup.name) {
                    this.showNotification('Group name is required.', 'warning');
                    return;
                }
                this.savingGroup = true;
                const isEditing = !!this.editingGroupId;
                const url = isEditing ? `/api/groups/${this.editingGroupId}` : '/api/groups/';
                const method = isEditing ? 'PUT' : 'POST';
                
                const payload = {
                    name: this.newGroup.name,
                    description: this.newGroup.description || null // Send null if empty
                };
                
                // Only include file_ids when creating a group (optional)
                // if (!isEditing && this.selectedFiles.length > 0) {
                //     payload.file_ids = this.selectedFiles;
                // }

                try {
                    const response = await fetch(url, {
                        method: method,
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(payload)
                    });
                     const result = await response.json();
                    if (!response.ok) {
                         throw new Error(result.detail || `HTTP error! Status: ${response.status}`);
                    }
                    this.createGroupModal.hide();
                    this.showNotification(`Group ${isEditing ? 'updated' : 'created'} successfully!`, 'success');
                    await this.loadGroups(); // Refresh the list
                     // If creating with selected files, clear selection
                     // if (!isEditing && payload.file_ids) {
                     //    this.clearSelection(); 
                     // }
                } catch (error) {
                    console.error(`Error ${isEditing ? 'updating' : 'saving'} group:`, error);
                    this.showNotification(`Error ${isEditing ? 'updating' : 'saving'} group: ${error.message}`, 'danger');
                } finally {
                     this.savingGroup = false;
                }
            },

            async viewGroupFiles(groupId) {
                this.currentGroup = this.groups.find(g => g.id === groupId);
                if (!this.currentGroup) return;
                
                this.groupFiles = [];
                this.loadingGroupFiles = true;
                this.groupFilesModal.show(); // Show modal immediately

                try {
                    const response = await fetch(`/api/groups/${groupId}/files`);
                     if (!response.ok) {
                        const errorData = await response.json().catch(() => ({ detail: `HTTP error! Status: ${response.status}` }));
                        throw new Error(errorData.detail);
                    }
                    this.groupFiles = await response.json();
                } catch (error) {
                    console.error("Error loading group files:", error);
                    this.showNotification(`Error loading files for group: ${error.message}`, 'danger');
                    this.groupFilesModal.hide(); // Hide modal on error
                } finally {
                    this.loadingGroupFiles = false;
                }
            },

            async deleteGroup(groupId) {
                const group = this.groups.find(g => g.id === groupId);
                if (!group) return;

                if (!confirm(`Are you sure you want to delete the group "${group.name}"? This cannot be undone.`)) {
                    return;
                }
                
                this.loadingGroups = true; // Use main group loading indicator
                try {
                    const response = await fetch(`/api/groups/${groupId}`, {
                        method: 'DELETE'
                    });
                     // Check for 204 No Content success
                     if (response.status === 204) {
                         this.showNotification(`Group "${group.name}" deleted successfully.`, 'success');
                     } else if (!response.ok) {
                         const errorData = await response.json().catch(() => ({ detail: `HTTP error! Status: ${response.status}` }));
                         throw new Error(errorData.detail);
                     } else {
                         // Handle unexpected success codes if necessary
                          this.showNotification(`Group "${group.name}" deleted. Status: ${response.status}`, 'info');
                     }
                    await this.loadGroups(); // Refresh the list
                } catch (error) {
                    console.error("Error deleting group:", error);
                    this.showNotification(`Error deleting group: ${error.message}`, 'danger');
                    this.loadingGroups = false; // Ensure loading stops on error
                }
                // No finally needed for loadingGroups here, as loadGroups handles it
            },

            async removeFileFromGroup(fileId) {
                if (!this.currentGroup) return;
                const file = this.groupFiles.find(f => f.id === fileId);
                 if (!file) return;

                if (!confirm(`Remove file "${file.filename}" from group "${this.currentGroup.name}"?`)) {
                    return;
                }
                
                // Indicate loading within the modal if desired (optional)
                // this.loadingGroupFiles = true; 

                try {
                    const response = await fetch(`/api/groups/${this.currentGroup.id}/files/${fileId}`, {
                        method: 'DELETE'
                    });
                     if (response.status === 204) {
                        this.showNotification(`File "${file.filename}" removed from group.`, 'success');
                         // Remove file from the local list instantly
                        this.groupFiles = this.groupFiles.filter(f => f.id !== fileId);
                        // Refresh the main group list in the background to update count
                         this.loadGroups(); 
                     } else if (!response.ok) {
                        const errorData = await response.json().catch(() => ({ detail: `HTTP error! Status: ${response.status}` }));
                         throw new Error(errorData.detail);
                     } else {
                         this.showNotification(`File removed status: ${response.status}`, 'info');
                         this.groupFiles = this.groupFiles.filter(f => f.id !== fileId);
                         this.loadGroups(); 
                     }
                } catch (error) {
                    console.error("Error removing file from group:", error);
                    this.showNotification(`Error removing file: ${error.message}`, 'danger');
                } finally {
                     // this.loadingGroupFiles = false; // Turn off modal loading indicator
                }
            },

            // --- Plotting Methods ---
            async loadAvailablePlots() {
                console.log("Loading available plots...");
                try {
                    const response = await fetch('/api/plots');
                    if (!response.ok) throw new Error('Failed to load plot types');
                    const data = await response.json();
                    this.availablePlots = data.plots || [];
                    this.populatePlotSelector(); // Call method to update dropdown
                } catch (error) {
                    console.error("Error loading available plots:", error);
                    this.showNotification("Error loading plot types", "danger");
                }
            },

            populatePlotSelector() {
                const select = document.getElementById('plot-select');
                if (!select) return;
                select.innerHTML = '<option value="">Choose a plot type...</option>'; 
                this.availablePlots.forEach(plot => {
                    const option = document.createElement('option');
                    option.value = plot.name; 
                    option.textContent = plot.display_name; 
                    select.appendChild(option);
                });
            },

            async loadPlotAvailableData(fileId) {
                if (!fileId) return;
                console.log(`Loading marker/channel data for file ID: ${fileId}`);
                // Indicate loading maybe? Optional
                try {
                    // Fetch markers
                    const markerUrl = `/api/plot/markers?file_id=${fileId}`;
                    const markerResponse = await fetch(markerUrl);
                    if (!markerResponse.ok) throw new Error(`Markers HTTP error! Status: ${markerResponse.status}`);
                    const markerData = await markerResponse.json();
                    this.plotMarkerOptions = markerData.markers || []; // Store options
                    // Don't populate here - let watcher handle it
                    // this.populateMarkerSelect(); 

                    // Fetch channels
                    const channelUrl = `/api/plot/channels?file_id=${fileId}`;
                    const channelResponse = await fetch(channelUrl);
                    if (!channelResponse.ok) throw new Error(`Channels HTTP error! Status: ${channelResponse.status}`);
                    const channelData = await channelResponse.json();
                    this.plotChannelOptions = channelData.channels || []; // Store options
                     // Don't populate here - let watcher handle it
                    // this.populateChannelSelect();

                } catch (error) {
                    console.error('Error loading plot marker/channel data:', error);
                    this.showNotification(`Error loading options: ${error.message}`, 'danger');
                    this.plotMarkerOptions = [];
                    this.plotChannelOptions = [];
                    // Clear selectors if visible
                    this.$nextTick(() => {
                        this.populateMarkerSelect();
                        this.populateChannelSelect();
                    });
                }
            },

            populateMarkerSelect() {
                const select = document.getElementById('marker-select');
                // Guard against the element not existing (important!)
                if (!select) {
                     console.warn("[populateMarkerSelect] Marker select element not found.");
                     return;
                }
                console.log(`[populateMarkerSelect] Populating with ${this.plotMarkerOptions.length} options.`);
                select.innerHTML = ''; // Clear previous options
                this.plotMarkerOptions.forEach(marker => {
                    const option = document.createElement('option');
                    option.value = marker;
                    option.textContent = marker;
                    select.appendChild(option);
                });
            },

            populateChannelSelect() {
                const select = document.getElementById('channel-select');
                 // Guard against the element not existing (important!)
                if (!select) {
                    console.warn("[populateChannelSelect] Channel select element not found.");
                    return;
                }
                console.log(`[populateChannelSelect] Populating with ${this.plotChannelOptions.length} options.`);
                select.innerHTML = ''; // Clear previous options
                this.plotChannelOptions.forEach(channel => {
                    const option = document.createElement('option');
                    option.value = channel;
                    option.textContent = channel;
                    select.appendChild(option);
                });
            },
            
            clearPlot() {
                const container = document.getElementById('plot-container');
                // Add check for container existence
                if (container) {
                    try {
                        Plotly.purge(container); // Use container element directly
                    } catch(e) { 
                         console.warn("[clearPlot] Error purging Plotly:", e);
                    }
                    container.innerHTML = ''; // Clear any remaining content (like error messages)
                } else {
                     console.warn("[clearPlot] Plot container not found.");
                }
            },

            async updatePlot() {
                if (!this.selectedFileId || !this.selectedPlot) {
                    this.showNotification("Please select a file and a plot type.", "warning");
                    return;
                }

                const fileId = this.selectedFileId;
                console.log(`Updating plot for file ID: ${fileId}, Plot: ${this.selectedPlot}`);
                this.isPlotLoading = true;
                this.clearPlot(); 

                try {
                    const markerSelect = document.getElementById('marker-select');
                    const channelSelect = document.getElementById('channel-select');
                    
                    const selectedMarkers = markerSelect ? Array.from(markerSelect.selectedOptions).map(option => option.value) : [];
                    const selectedChannels = channelSelect ? Array.from(channelSelect.selectedOptions).map(option => option.value) : [];

                    const parameters = {};
                    if (this.selectedPlotDetails?.requires_markers) {
                        parameters.markers = selectedMarkers;
                    }
                    if (this.selectedPlotDetails?.requires_channels) {
                        parameters.channels = selectedChannels;
                    }

                    const encodedParams = encodeURIComponent(JSON.stringify(parameters));
                    const plotDataUrl = `/api/plot?file_id=${fileId}&plot_name=${encodeURIComponent(this.selectedPlot)}&parameters=${encodedParams}`;
                    console.log(`Fetching plot data from: ${plotDataUrl}`);
                    const response = await fetch(plotDataUrl);

                    if (!response.ok) {
                        const errorText = await response.text();
                        throw new Error(`Plot data HTTP error! Status: ${response.status} - ${errorText}`);
                    }
                    const data = await response.json();

                    const traces = data.traces || [];
                    const layout = data.layout || {};
                    const config = data.config || {};

                    const plotDiv = document.getElementById('plot-container');
                    // Add check for plotDiv existence
                    if (!plotDiv) { 
                        throw new Error("Plot container not found in DOM!"); 
                    }
                    
                    Plotly.newPlot(plotDiv, traces, layout, config);
                    
                    // Also check before resizing
                    if(plotDiv) {
                        try {
                            Plotly.Plots.resize(plotDiv);
                        } catch (resizeError) {
                            console.warn("[Debug] Error calling Plotly resize:", resizeError);
                        }
                    }
                } catch (error) {
                    console.error("Error updating plot:", error);
                    const container = document.getElementById('plot-container');
                    if(container) {
                         container.innerHTML = 
                            `<div class="alert alert-danger">Error generating plot: ${error.message}</div>`;
                    } else {
                        this.showNotification(`Error generating plot: ${error.message}`, "danger");
                    }
                } finally {
                    this.isPlotLoading = false;
                }
            }
        },
        watch: {
            selectedFiles(newValue, oldValue) {
                console.log(`[Debug] Watcher: selectedFiles changed.`);
                console.log(`  Old value:`, JSON.stringify(oldValue));
                console.log(`  New value:`, JSON.stringify(newValue));
            },
            // Watch for file selection changes relevant to plotting
            selectedFileId(newFileId, oldFileId) {
                if (newFileId !== oldFileId) {
                    console.log("[Plot Watcher] File changed, loading available data...");
                    this.plotMarkerOptions = []; // Clear old options
                    this.plotChannelOptions = [];
                    this.selectedPlotDetails = null; // Also reset plot details
                    // this.selectedPlot = null; // Optionally reset plot selection too
                    this.clearPlot();
                    if (newFileId) {
                        this.loadPlotAvailableData(newFileId); // Load data, but don't populate yet
                    } else {
                        // Clear selectors if file is deselected
                         const markerSelect = document.getElementById('marker-select');
                         if (markerSelect) markerSelect.innerHTML = '';
                         const channelSelect = document.getElementById('channel-select');
                         if (channelSelect) channelSelect.innerHTML = '';
                    }
                }
            },
             // Watch for plot type changes
            selectedPlot(newPlotName, oldPlotName) {
                if (newPlotName !== oldPlotName) {
                    console.log("[Plot Watcher] Plot type changed...");
                    this.selectedPlotDetails = this.availablePlots.find(p => p.name === newPlotName) || null;
                    this.clearPlot();
                    // Selectors will be shown/hidden by computed props and v-if
                    // Population will be triggered by the showMarker/ChannelSelector watchers if needed
                }
            },
            // NEW: Watcher to populate marker select when it becomes visible
            showMarkerSelector(isVisible) {
                if (isVisible) {
                    console.log("[Plot Watcher] Marker selector now visible, populating...");
                    // Use nextTick to ensure the element is in the DOM after v-if becomes true
                    this.$nextTick(() => {
                        this.populateMarkerSelect();
                    });
                }
            },
            // NEW: Watcher to populate channel select when it becomes visible
            showChannelSelector(isVisible) {
                if (isVisible) {
                    console.log("[Plot Watcher] Channel selector now visible, populating...");
                    // Use nextTick to ensure the element is in the DOM after v-if becomes true
                     this.$nextTick(() => {
                        this.populateChannelSelect();
                    });
                }
            }
        },
        mounted() {
            console.log("[Debug] Vue instance mounted. Calling initial methods...");
            this.initializeComponents();
            this.loadClassifications();
            this.loadAnalyses();
            this.loadGroups(); // Load groups on initial mount
            this.searchFiles();
            this.loadAvailablePlots(); // Load plot types on mount
        }
    });
    console.log("[Debug] Vue instance created.", app);
}); // Close DOMContentLoaded listener