// Enable Vue debugging
Vue.config.devtools = true;
Vue.config.debug = true;
Vue.config.performance = true;

document.addEventListener('DOMContentLoaded', function() {
    // Create Vue instance with proper configuration ONLY after DOM is ready
    window.app = new Vue({
        el: '#app',
        delimiters: ['{{', '}}'],  // Explicitly set template delimiters
        data: function() {  // Convert to function syntax for clarity
            return {
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
                
                // --- Hierarchy Data ---
                hierarchyData: {
                    classifications: [],
                    subjects: [],
                    sessions: [],
                    trials: []
                },
                hierarchyFilters: {
                    classificationId: '',
                    subjectId: '',
                    sessionId: ''
                },
                loadingHierarchy: false,
                selectedTrial: null,
                
                // Classification form data
                classificationForm: {
                    name: '',
                    description: '',
                    meta_data_json: '{}'
                },
                editingClassificationId: null,
                savingClassification: false,
                metaDataJsonError: null,
                
                // Subject form data
                subjectForm: {
                    name: '',
                    description: '',
                    classification_id: null,
                    demographics_json: '{}'
                },
                editingSubjectId: null,
                savingSubject: false,
                demographicsJsonError: null,
                
                // Session form data
                sessionForm: {
                    name: '',
                    description: '',
                    subject_id: null,
                    date: '',
                    conditions_json: '{}'
                },
                editingSessionId: null,
                savingSession: false,
                conditionsJsonError: null,
                
                // Trial form data
                trialForm: {
                    name: '',
                    description: '',
                    session_id: null,
                    c3d_file_id: null,
                    parameters_json: '{}'
                },
                editingTrialId: null,
                savingTrial: false,
                parametersJsonError: null,
                availableC3DFiles: [],
                
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
                
                // Group file detail view
                viewingFileInGroup: false,
                selectedGroupFileDetails: null,
                loadingGroupFileDetails: false,
                
                // --- Plotting Data ---
                availablePlots: [],
                selectedPlot: null,
                selectedPlotDetails: null,
                isPlotLoading: false,
                plotMarkerOptions: [], // Separate options for selectors
                plotChannelOptions: [], // Separate options for selectors
                selectedFileId: null, // ID of the file selected in the plot tab
                
                // --- Directory Scan UI ---
                showDirectoryScanFloatingCard: false, // Controls visibility of the floating directory scan card
                savedGroupModalState: null,
            };
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
                // Initialize Bootstrap modals
                try {
                    this.fileDetailsModal = new bootstrap.Modal(document.getElementById('fileDetailsModal'));
                    this.addToGroupModal = new bootstrap.Modal(document.getElementById('addToGroupModal'));
                    this.createGroupModal = new bootstrap.Modal(document.getElementById('createGroupModal'));
                    this.groupFilesModal = new bootstrap.Modal(document.getElementById('groupFilesModal'));
                    
                    // Initialize hierarchy modals
                    this.initializeHierarchyModals();
                } catch (error) {
                    console.error("Error initializing Bootstrap modals:", error);
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
                            this.refreshHierarchy();
                        }, 5000); // Try checking after 5 seconds
                    } else {
                        // Handle case when old API endpoint is still being used
                        this.directoryStatus = `<div class="alert alert-success">Successfully indexed ${data.indexed?.length || 0} files</div>`;
                        this.loadClassifications();
                        this.searchFiles();
                        this.refreshHierarchy();
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
                
                fetch(`/api/files/?${params.toString()}`)
                    .then(response => {
                        if (!response.ok) {
                            throw new Error(`HTTP error! Status: ${response.status}`);
                        }
                        return response.json();
                    })
                    .then(data => {
                        this.files = data.files || [];
                        this.fileTree = this.buildFileTree(this.files);
                        this.fileCountInfo = `Total: ${data.pagination?.filtered || 0} of ${data.pagination?.total || 0} files`;
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
            showFileDetails(fileIdOrObject) {
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
                
                // Store the current modal state to restore it later if needed
                this.savedGroupModalState = {
                    currentGroup: this.currentGroup,
                    groupFiles: [...this.groupFiles],
                    fromGroupView: !!this.currentGroup
                };
                
                // Show the file details modal
                this.fileDetailsModal.show();
                
                // Check if we were passed a file object directly
                if (typeof fileIdOrObject === 'object' && fileIdOrObject !== null) {
                    // We have the file object already - no need to fetch
                    const file = fileIdOrObject;
                    this.renderFileDetails(file, modalTitle, modalBody, downloadBtn);
                    return;
                }
                
                // Otherwise, treat it as a file ID
                const fileId = fileIdOrObject;
                
                // Try to get the file from our file cache first (files or groupFiles)
                let targetFile = null;
                if (this.groupFiles.length > 0) {
                    targetFile = this.groupFiles.find(f => f.id === fileId);
                }
                if (!targetFile && this.files.length > 0) {
                    targetFile = this.files.find(f => f.id === fileId);
                }
                
                // If we found the file in our cache, use it directly 
                if (targetFile) {
                    this.renderFileDetails(targetFile, modalTitle, modalBody, downloadBtn);
                    return;
                }
                
                // Otherwise fetch it from the API - first try by filepath if we know it
                let apiUrl = `/api/files/id/${fileId}`;  // Default to ID-based endpoint
                
                fetch(apiUrl)
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP error! Status: ${response.status}`);
                    }
                    return response.json();
                })
                .then(file => {
                    this.renderFileDetails(file, modalTitle, modalBody, downloadBtn);
                })
                .catch(error => {
                    modalBody.innerHTML = `
                        <div class="alert alert-danger">Error loading file details: ${error.message}</div>
                        ${this.savedGroupModalState.fromGroupView ? 
                          `<button class="btn btn-secondary" onclick="app.returnToGroupView()">
                               <i class="bi bi-arrow-left"></i> Back to Group
                           </button>` : ''}
                    `;
                });
            },
            
            // Helper method to render file details
            renderFileDetails(file, modalTitle, modalBody, downloadBtn) {
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
                
                // Add a "back to group" link if we're coming from a group view
                const backToGroupLink = this.savedGroupModalState.fromGroupView ? 
                    `<button class="btn btn-sm btn-outline-secondary mb-3" onclick="app.returnToGroupView()">
                        <i class="bi bi-arrow-left"></i> Back to Group
                     </button>` : '';
                
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
                    ${backToGroupLink}
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
                downloadBtn.href = `/api/files/download?path=${encodeURIComponent(file.filepath)}`;
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
                if (!bytes) return 'Unknown';
                const units = ['B', 'KB', 'MB', 'GB'];
                let size = bytes;
                let unitIndex = 0;
                
                while (size >= 1024 && unitIndex < units.length - 1) {
                    size /= 1024;
                    unitIndex++;
                }
                
                return `${size.toFixed(2)} ${units[unitIndex]}`;
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
                    const date = new Date(dateString);
                    return date.toLocaleString();
                } catch (error) {
                    return dateString;
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
                    } catch (e) {
                        console.error("Error calling createGroupModal.show():", e);
                    }
                });
            },

            showEditGroupModal(group) {
                 console.log(`[Debug] showEditGroupModal called for group: ${group.id}`);
                this.editingGroupId = group.id;
                this.newGroup = { name: group.name, description: group.description };
                // Wait for Vue to update the DOM based on editingGroupId having a value
                 this.$nextTick(() => {
                    try {
                        this.createGroupModal.show();
                    } catch (e) {
                        console.error("Error calling createGroupModal.show() for editing:", e);
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
                
                // Reset file details view
                this.viewingFileInGroup = false;
                this.selectedGroupFileDetails = null;

                // Show modal immediately
                this.groupFilesModal.show();
                
                // Add a modal shown event listener to handle resize
                const modalElement = document.getElementById('groupFilesModal');
                if (modalElement) {
                    modalElement.addEventListener('shown.bs.modal', () => {
                        window.dispatchEvent(new Event('resize'));
                    }, { once: true });
                }

                try {
                    const response = await fetch(`/api/groups/${groupId}/files`);
                     if (!response.ok) {
                        const errorData = await response.json().catch(() => ({ detail: `HTTP error! Status: ${response.status}` }));
                        throw new Error(errorData.detail);
                    }
                    this.groupFiles = await response.json();
                    console.log("Loaded group files:", this.groupFiles.length);
                } catch (error) {
                    console.error("Error loading group files:", error);
                    this.showNotification(`Error loading group files: ${error.message}`, 'danger');
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
                }
            },

            // View file details within the group modal
            async showFileDetailsInGroup(fileId) {
                console.log("showFileDetailsInGroup called with fileId:", fileId);
                
                // Hide the group files modal
                this.groupFilesModal.hide();
                
                // Get the file from our groupFiles array
                const file = this.groupFiles.find(f => f.id === fileId);
                if (!file) {
                    this.showNotification("File not found in group", 'danger');
                    return;
                }
                
                // Show the file details in the standalone modal with the file object directly
                this.showFileDetails(file);
            },
            
            // Hide file details panel and return to group view
            hideFileDetailsInGroup() {
                this.viewingFileInGroup = false;
                this.selectedGroupFileDetails = null;
            },

            // --- Plotting Methods ---
            async loadAvailablePlots() {
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
                try {
                    // Fetch markers
                    const markerUrl = `/api/plot/markers?file_id=${fileId}`;
                    const markerResponse = await fetch(markerUrl);
                    if (!markerResponse.ok) throw new Error(`Markers HTTP error! Status: ${markerResponse.status}`);
                    const markerData = await markerResponse.json();
                    this.plotMarkerOptions = markerData.markers || []; // Store options

                    // Fetch channels
                    const channelUrl = `/api/plot/channels?file_id=${fileId}`;
                    const channelResponse = await fetch(channelUrl);
                    if (!channelResponse.ok) throw new Error(`Channels HTTP error! Status: ${channelResponse.status}`);
                    const channelData = await channelResponse.json();
                    this.plotChannelOptions = channelData.channels || []; // Store options

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
                // Guard against the element not existing
                if (!select) return;
                
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
                // Guard against the element not existing
                if (!select) return;
                
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
                        console.warn("Error purging Plotly:", e);
                    }
                    container.innerHTML = ''; // Clear any remaining content (like error messages)
                }
            },

            async updatePlot() {
                if (!this.selectedFileId || !this.selectedPlot) {
                    this.showNotification("Please select a file and a plot type.", "warning");
                    return;
                }

                const fileId = this.selectedFileId;
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
                            console.warn("Error calling Plotly resize:", resizeError);
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
            },

            // --- Hierarchy methods ---
            initializeHierarchyModals() {
                // Initialize hierarchy modals
                try {
                    this.classificationModal = new bootstrap.Modal(document.getElementById('classificationModal'));
                    this.subjectModal = new bootstrap.Modal(document.getElementById('subjectModal'));
                    this.sessionModal = new bootstrap.Modal(document.getElementById('sessionModal'));
                    this.trialModal = new bootstrap.Modal(document.getElementById('trialModal'));
                    this.trialResultsModal = new bootstrap.Modal(document.getElementById('trialResultsModal'));
                } catch (error) {
                    console.error("Error initializing hierarchy modals:", error);
                }
                
                // Reset forms when modals are hidden
                document.getElementById('classificationModal').addEventListener('hidden.bs.modal', () => {
                    this.editingClassificationId = null;
                    this.classificationForm = { name: '', description: '', meta_data_json: '{}' };
                    this.metaDataJsonError = null;
                    this.savingClassification = false;
                });
                
                document.getElementById('subjectModal').addEventListener('hidden.bs.modal', () => {
                    this.editingSubjectId = null;
                    this.subjectForm = { name: '', description: '', classification_id: null, demographics_json: '{}' };
                    this.demographicsJsonError = null;
                    this.savingSubject = false;
                });
                
                document.getElementById('sessionModal').addEventListener('hidden.bs.modal', () => {
                    this.editingSessionId = null;
                    this.sessionForm = { name: '', description: '', subject_id: null, date: '', conditions_json: '{}' };
                    this.conditionsJsonError = null;
                    this.savingSession = false;
                });
                
                document.getElementById('trialModal').addEventListener('hidden.bs.modal', () => {
                    this.editingTrialId = null;
                    this.trialForm = { name: '', description: '', session_id: null, c3d_file_id: null, parameters_json: '{}' };
                    this.parametersJsonError = null;
                    this.savingTrial = false;
                });
                
                document.getElementById('trialResultsModal').addEventListener('hidden.bs.modal', () => {
                    this.selectedTrial = null;
                });
            },
            
            refreshHierarchy() {
                // If we have specific filters set, use the specific loading methods
                if (this.hierarchyFilters.sessionId) {
                    this.loadHierarchyTrials();
                } else if (this.hierarchyFilters.subjectId) {
                    this.loadHierarchySessions().then(() => this.loadHierarchyTrials());
                } else if (this.hierarchyFilters.classificationId) {
                    this.loadHierarchySubjects()
                      .then(() => this.loadHierarchySessions())
                      .then(() => this.loadHierarchyTrials());
                } else {
                    // Otherwise load everything
                    this.loadHierarchyClassifications()
                      .then(() => this.loadAllSubjects())
                      .then(() => this.loadAllSessions())
                      .then(() => this.loadAllTrials())
                      .catch(error => {
                        console.error("Error refreshing hierarchy data:", error);
                      });
                }
                
                // Also refresh the file search to update any listings
                this.searchFiles();
            },
            
            async loadHierarchyClassifications() {
                this.loadingHierarchy = true;
                try {
                    const response = await fetch('/api/classifications/');
                    if (!response.ok) {
                        throw new Error(`Failed to load classifications: ${response.statusText}`);
                    }
                    
                    const data = await response.json();
                    this.hierarchyData.classifications = data;
                    return data; // Return the data for promise chaining
                } catch (error) {
                    console.error("Error loading classifications:", error);
                    this.showNotification(`Error loading classifications: ${error.message}`, 'danger');
                    throw error; // Re-throw to allow promise catch chaining
                } finally {
                    this.loadingHierarchy = false;
                }
            },
            
            async loadAllSubjects() {
                this.loadingHierarchy = true;
                try {
                    const response = await fetch('/api/subjects/');
                    if (!response.ok) {
                        throw new Error(`Failed to load subjects: ${response.statusText}`);
                    }
                    
                    const data = await response.json();
                    this.hierarchyData.subjects = data;
                    return data; // Return the data for promise chaining
                } catch (error) {
                    console.error("Error loading all subjects:", error);
                    this.showNotification(`Error loading subjects: ${error.message}`, 'danger');
                    throw error; // Re-throw to allow promise catch chaining
                } finally {
                    this.loadingHierarchy = false;
                }
            },
            
            async loadAllSessions() {
                this.loadingHierarchy = true;
                try {
                    const response = await fetch('/api/sessions/');
                    if (!response.ok) {
                        throw new Error(`Failed to load sessions: ${response.statusText}`);
                    }
                    
                    const data = await response.json();
                    this.hierarchyData.sessions = data;
                    return data; // Return the data for promise chaining
                } catch (error) {
                    console.error("Error loading all sessions:", error);
                    this.showNotification(`Error loading sessions: ${error.message}`, 'danger');
                    throw error; // Re-throw to allow promise catch chaining
                } finally {
                    this.loadingHierarchy = false;
                }
            },
            
            async loadAllTrials() {
                this.loadingHierarchy = true;
                try {
                    const response = await fetch('/api/trials/');
                    if (!response.ok) {
                        throw new Error(`Failed to load trials: ${response.statusText}`);
                    }
                    
                    const data = await response.json();
                    this.hierarchyData.trials = data;
                    return data;
                } catch (error) {
                    console.error("Error loading trials for session:", error);
                    this.showNotification(`Error loading trials: ${error.message}`, 'danger');
                    throw error;
                } finally {
                    this.loadingHierarchy = false;
                }
            },
            
            showTrialResults(trialId) {
                this.loadingHierarchy = true;
                fetch(`/api/trials/${trialId}`)
                    .then(response => {
                        if (!response.ok) {
                            throw new Error(`Failed to load trial: ${response.statusText}`);
                        }
                        return response.json();
                    })
                    .then(data => {
                        this.selectedTrial = data;
                        this.trialResultsModal.show();
                    })
                    .catch(error => {
                        console.error(`Error loading trial ${trialId}:`, error);
                        this.showNotification(`Error loading trial: ${error.message}`, 'danger');
                    })
                    .finally(() => {
                        this.loadingHierarchy = false;
                    });
            },
            
            showCreateClassificationModal() {
                this.editingClassificationId = null;
                this.classificationForm = {
                    name: '',
                    description: '',
                    meta_data_json: '{}'
                };
                this.metaDataJsonError = null;
                this.classificationModal.show();
            },
            
            showEditClassificationModal(classification) {
                this.editingClassificationId = classification.id;
                this.classificationForm = {
                    name: classification.name,
                    description: classification.description || '',
                    meta_data_json: JSON.stringify(classification.meta_data || {}, null, 2)
                };
                this.metaDataJsonError = null;
                this.classificationModal.show();
            },
            
            saveClassification() {
                // Validate form
                if (!this.classificationForm.name) {
                    this.showNotification('Classification name is required', 'warning');
                    return;
                }
                
                // Parse JSON
                let meta_data;
                try {
                    meta_data = JSON.parse(this.classificationForm.meta_data_json);
                } catch (error) {
                    this.metaDataJsonError = 'Invalid JSON format: ' + error.message;
                    return;
                }
                
                // Prepare data
                const data = {
                    name: this.classificationForm.name,
                    description: this.classificationForm.description,
                    meta_data: meta_data
                };
                
                // Save classification
                this.savingClassification = true;
                
                // Determine if creating new or updating existing
                const url = this.editingClassificationId 
                    ? `/api/classifications/${this.editingClassificationId}` 
                    : '/api/classifications/';
                    
                const method = this.editingClassificationId ? 'PUT' : 'POST';
                
                fetch(url, {
                    method: method,
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(data)
                })
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`Failed to save classification: ${response.statusText}`);
                    }
                    return response.json();
                })
                .then(data => {
                    this.classificationModal.hide();
                    this.showNotification(`Classification ${this.editingClassificationId ? 'updated' : 'created'} successfully`, 'success');
                    this.loadHierarchyClassifications();
                })
                .catch(error => {
                    console.error("Error saving classification:", error);
                    this.showNotification(`Error saving classification: ${error.message}`, 'danger');
                })
                .finally(() => {
                    this.savingClassification = false;
                });
            },
            
            showCreateSubjectModal() {
                this.editingSubjectId = null;
                this.subjectForm = {
                    name: '',
                    description: '',
                    classification_id: this.hierarchyFilters.classificationId || null,
                    demographics_json: '{}'
                };
                this.demographicsJsonError = null;
                this.subjectModal.show();
            },
            
            showEditSubjectModal(subject) {
                this.editingSubjectId = subject.id;
                this.subjectForm = {
                    name: subject.name,
                    description: subject.description || '',
                    classification_id: subject.classification_id,
                    demographics_json: JSON.stringify(subject.demographics || {}, null, 2)
                };
                this.demographicsJsonError = null;
                this.subjectModal.show();
            },
            
            saveSubject() {
                // Validate form
                if (!this.subjectForm.name) {
                    this.showNotification('Subject name is required', 'warning');
                    return;
                }
                
                if (!this.subjectForm.classification_id) {
                    this.showNotification('Classification is required', 'warning');
                    return;
                }
                
                // Parse JSON
                let demographics;
                try {
                    demographics = JSON.parse(this.subjectForm.demographics_json);
                } catch (error) {
                    this.demographicsJsonError = 'Invalid JSON format: ' + error.message;
                    return;
                }
                
                // Prepare data
                const data = {
                    name: this.subjectForm.name,
                    description: this.subjectForm.description,
                    classification_id: this.subjectForm.classification_id,
                    demographics: demographics
                };
                
                // Save subject
                this.savingSubject = true;
                
                // Determine if creating new or updating existing
                const url = this.editingSubjectId 
                    ? `/api/subjects/${this.editingSubjectId}` 
                    : '/api/subjects/';
                    
                const method = this.editingSubjectId ? 'PUT' : 'POST';
                
                fetch(url, {
                    method: method,
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(data)
                })
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`Failed to save subject: ${response.statusText}`);
                    }
                    return response.json();
                })
                .then(data => {
                    this.subjectModal.hide();
                    this.showNotification(`Subject ${this.editingSubjectId ? 'updated' : 'created'} successfully`, 'success');
                    this.loadHierarchySubjects();
                })
                .catch(error => {
                    console.error("Error saving subject:", error);
                    this.showNotification(`Error saving subject: ${error.message}`, 'danger');
                })
                .finally(() => {
                    this.savingSubject = false;
                });
            },
            
            showCreateSessionModal() {
                this.editingSessionId = null;
                this.sessionForm = {
                    name: '',
                    description: '',
                    subject_id: this.hierarchyFilters.subjectId || null,
                    date: new Date().toISOString().slice(0, 16), // Current date-time in ISO format
                    conditions_json: '{}'
                };
                this.conditionsJsonError = null;
                this.sessionModal.show();
            },
            
            showEditSessionModal(session) {
                this.editingSessionId = session.id;
                this.sessionForm = {
                    name: session.name,
                    description: session.description || '',
                    subject_id: session.subject_id,
                    date: session.date ? new Date(session.date).toISOString().slice(0, 16) : '',
                    conditions_json: JSON.stringify(session.conditions || {}, null, 2)
                };
                this.conditionsJsonError = null;
                this.sessionModal.show();
            },
            
            saveSession() {
                // Validate form
                if (!this.sessionForm.name) {
                    this.showNotification('Session name is required', 'warning');
                    return;
                }
                
                if (!this.sessionForm.subject_id) {
                    this.showNotification('Subject is required', 'warning');
                    return;
                }
                
                // Parse JSON
                let conditions;
                try {
                    conditions = JSON.parse(this.sessionForm.conditions_json);
                } catch (error) {
                    this.conditionsJsonError = 'Invalid JSON format: ' + error.message;
                    return;
                }
                
                // Prepare data
                const data = {
                    name: this.sessionForm.name,
                    description: this.sessionForm.description,
                    subject_id: this.sessionForm.subject_id,
                    date: this.sessionForm.date || null,
                    conditions: conditions
                };
                
                // Save session
                this.savingSession = true;
                
                // Determine if creating new or updating existing
                const url = this.editingSessionId 
                    ? `/api/sessions/${this.editingSessionId}` 
                    : '/api/sessions/';
                    
                const method = this.editingSessionId ? 'PUT' : 'POST';
                
                fetch(url, {
                    method: method,
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(data)
                })
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`Failed to save session: ${response.statusText}`);
                    }
                    return response.json();
                })
                .then(data => {
                    this.sessionModal.hide();
                    this.showNotification(`Session ${this.editingSessionId ? 'updated' : 'created'} successfully`, 'success');
                    this.loadHierarchySessions();
                })
                .catch(error => {
                    console.error("Error saving session:", error);
                    this.showNotification(`Error saving session: ${error.message}`, 'danger');
                })
                .finally(() => {
                    this.savingSession = false;
                });
            },
            
            // Load available C3D files for the trial form
            async loadAvailableC3DFiles() {
                try {
                    const response = await fetch('/api/files/');
                    if (!response.ok) {
                        throw new Error(`Failed to load C3D files: ${response.statusText}`);
                    }
                    
                    const data = await response.json();
                    this.availableC3DFiles = data;
                } catch (error) {
                    console.error("Error loading C3D files:", error);
                    this.showNotification(`Error loading C3D files: ${error.message}`, 'danger');
                }
            },
            
            showCreateTrialModal() {
                this.loadAvailableC3DFiles();
                this.editingTrialId = null;
                this.trialForm = {
                    name: '',
                    description: '',
                    session_id: this.hierarchyFilters.sessionId || null,
                    c3d_file_id: null,
                    parameters_json: '{}'
                };
                this.parametersJsonError = null;
                this.trialModal.show();
            },
            
            showEditTrialModal(trial) {
                this.loadAvailableC3DFiles();
                this.editingTrialId = trial.id;
                this.trialForm = {
                    name: trial.name,
                    description: trial.description || '',
                    session_id: trial.session_id,
                    c3d_file_id: trial.c3d_file_id || null,
                    parameters_json: JSON.stringify(trial.parameters || {}, null, 2)
                };
                this.parametersJsonError = null;
                this.trialModal.show();
            },
            
            saveTrial() {
                // Validate form
                if (!this.trialForm.name) {
                    this.showNotification('Trial name is required', 'warning');
                    return;
                }
                
                if (!this.trialForm.session_id) {
                    this.showNotification('Session is required', 'warning');
                    return;
                }
                
                // Parse JSON
                let parameters;
                try {
                    parameters = JSON.parse(this.trialForm.parameters_json);
                } catch (error) {
                    this.parametersJsonError = 'Invalid JSON format: ' + error.message;
                    return;
                }
                
                // Prepare data
                const data = {
                    name: this.trialForm.name,
                    description: this.trialForm.description,
                    session_id: this.trialForm.session_id,
                    c3d_file_id: this.trialForm.c3d_file_id || null,
                    parameters: parameters
                };
                
                // Save trial
                this.savingTrial = true;
                
                // Determine if creating new or updating existing
                const url = this.editingTrialId 
                    ? `/api/trials/${this.editingTrialId}` 
                    : '/api/trials/';
                    
                const method = this.editingTrialId ? 'PUT' : 'POST';
                
                fetch(url, {
                    method: method,
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(data)
                })
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`Failed to save trial: ${response.statusText}`);
                    }
                    return response.json();
                })
                .then(data => {
                    this.trialModal.hide();
                    this.showNotification(`Trial ${this.editingTrialId ? 'updated' : 'created'} successfully`, 'success');
                    this.loadHierarchyTrials();
                })
                .catch(error => {
                    console.error("Error saving trial:", error);
                    this.showNotification(`Error saving trial: ${error.message}`, 'danger');
                })
                .finally(() => {
                    this.savingTrial = false;
                });
            },
            
            validateJson(field) {
                try {
                    if (field === 'parameters') {
                        JSON.parse(this.trialForm.parameters_json);
                        this.parametersJsonError = null;
                    } else if (field === 'meta_data') {
                        JSON.parse(this.classificationForm.meta_data_json);
                        this.metaDataJsonError = null;
                    } else if (field === 'demographics') {
                        JSON.parse(this.subjectForm.demographics_json);
                        this.demographicsJsonError = null;
                    } else if (field === 'conditions') {
                        JSON.parse(this.sessionForm.conditions_json);
                        this.conditionsJsonError = null;
                    }
                } catch (error) {
                    if (field === 'parameters') {
                        this.parametersJsonError = 'Invalid JSON format: ' + error.message;
                    } else if (field === 'meta_data') {
                        this.metaDataJsonError = 'Invalid JSON format: ' + error.message;
                    } else if (field === 'demographics') {
                        this.demographicsJsonError = 'Invalid JSON format: ' + error.message;
                    } else if (field === 'conditions') {
                        this.conditionsJsonError = 'Invalid JSON format: ' + error.message;
                    }
                }
            },
            
            deleteTrial(trialId) {
                if (!confirm('Are you sure you want to delete this trial? This action cannot be undone.')) {
                    return;
                }
                
                this.loadingHierarchy = true;
                fetch(`/api/trials/${trialId}`, {
                    method: 'DELETE'
                })
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`Failed to delete trial: ${response.statusText}`);
                    }
                    
                    this.showNotification('Trial deleted successfully', 'success');
                    this.loadHierarchyTrials();
                })
                .catch(error => {
                    console.error(`Error deleting trial ${trialId}:`, error);
                    this.showNotification(`Error deleting trial: ${error.message}`, 'danger');
                })
                .finally(() => {
                    this.loadingHierarchy = false;
                });
            },
            
            // Show the floating directory scan card
            showDirectoryScanCard() {
                this.showDirectoryScanFloatingCard = true;
                this.directoryStatus = ''; // Clear any previous status messages
                // Set focus on the directory input field
                this.$nextTick(() => {
                    document.getElementById('directoryInput')?.focus();
                    // Initialize tooltips for the floating card
                    const tooltips = document.querySelectorAll('.position-fixed [data-bs-toggle="tooltip"]');
                    [...tooltips].forEach(el => new bootstrap.Tooltip(el));
                });
            },
            
            // Hide the floating directory scan card
            hideDirectoryScanCard() {
                this.showDirectoryScanFloatingCard = false;
                this.directoryStatus = '';
                this.directoryPath = '';
            },
            
            // Show help information about getting directory paths
            showPathHelpInfo() {
                const osInfo = navigator.userAgent.indexOf('Win') !== -1 ? 'Windows' : 
                              (navigator.userAgent.indexOf('Mac') !== -1 ? 'macOS' : 'Linux');
                
                let helpText = '<div class="alert alert-info">';
                helpText += '<h6>How to find your directory path:</h6>';
                
                if (osInfo === 'Windows') {
                    helpText += '<ol class="mb-0">' + 
                        '<li>Open File Explorer and navigate to your folder</li>' + 
                        '<li>Click in the address bar (or press Alt+D)</li>' + 
                        '<li>The full path will be highlighted - press Ctrl+C to copy</li>' + 
                        '<li>Paste it here using Ctrl+V</li>' + 
                        '</ol>';
                } else if (osInfo === 'macOS') {
                    helpText += '<ol class="mb-0">' + 
                        '<li>Open Finder and navigate to your folder</li>' + 
                        '<li>Right-click on the folder and select "Get Info"</li>' + 
                        '<li>Copy the path from "Where:" field</li>' + 
                        '<li>Paste it here using Command+V</li>' + 
                        '</ol>';
                } else {
                    helpText += '<ol class="mb-0">' + 
                        '<li>Open your file manager and navigate to the folder</li>' + 
                        '<li>Right-click and select "Properties" or use the location bar</li>' + 
                        '<li>Copy the full path</li>' + 
                        '<li>Paste it here</li>' + 
                        '</ol>';
                }
                
                helpText += '</div>';
                
                this.directoryStatus = helpText;
            },
            
            // Filtered hierarchy loading methods
            async loadHierarchySubjects() {
                const classificationId = this.hierarchyFilters.classificationId;
                if (!classificationId) {
                    return this.loadAllSubjects();
                }
                
                this.loadingHierarchy = true;
                try {
                    const response = await fetch(`/api/subjects/?classification_id=${classificationId}`);
                    if (!response.ok) {
                        throw new Error(`Failed to load subjects: ${response.statusText}`);
                    }
                    
                    const data = await response.json();
                    this.hierarchyData.subjects = data;
                    
                    // Reset session selection
                    this.hierarchyFilters.subjectId = '';
                    this.hierarchyData.sessions = [];
                    this.hierarchyData.trials = [];
                    
                    return data;
                } catch (error) {
                    console.error("Error loading subjects for classification:", error);
                    this.showNotification(`Error loading subjects: ${error.message}`, 'danger');
                    throw error;
                } finally {
                    this.loadingHierarchy = false;
                }
            },
            
            async loadHierarchySessions() {
                const subjectId = this.hierarchyFilters.subjectId;
                if (!subjectId) {
                    return this.loadAllSessions();
                }
                
                this.loadingHierarchy = true;
                try {
                    const response = await fetch(`/api/sessions/?subject_id=${subjectId}`);
                    if (!response.ok) {
                        throw new Error(`Failed to load sessions: ${response.statusText}`);
                    }
                    
                    const data = await response.json();
                    this.hierarchyData.sessions = data;
                    
                    // Reset trial selection
                    this.hierarchyFilters.sessionId = '';
                    this.hierarchyData.trials = [];
                    
                    return data;
                } catch (error) {
                    console.error("Error loading sessions for subject:", error);
                    this.showNotification(`Error loading sessions: ${error.message}`, 'danger');
                    throw error;
                } finally {
                    this.loadingHierarchy = false;
                }
            },
            
            async loadHierarchyTrials() {
                const sessionId = this.hierarchyFilters.sessionId;
                if (!sessionId) {
                    return this.loadAllTrials();
                }
                
                this.loadingHierarchy = true;
                try {
                    const response = await fetch(`/api/trials/?session_id=${sessionId}`);
                    if (!response.ok) {
                        throw new Error(`Failed to load trials: ${response.statusText}`);
                    }
                    
                    const data = await response.json();
                    this.hierarchyData.trials = data;
                    return data;
                } catch (error) {
                    console.error("Error loading trials for session:", error);
                    this.showNotification(`Error loading trials: ${error.message}`, 'danger');
                    throw error;
                } finally {
                    this.loadingHierarchy = false;
                }
            },

            returnToGroupView() {
                // Close the file details modal
                this.fileDetailsModal.hide();
                
                // Restore the group modal if we have saved state
                if (this.savedGroupModalState && this.savedGroupModalState.fromGroupView) {
                    this.currentGroup = this.savedGroupModalState.currentGroup;
                    this.groupFiles = [...this.savedGroupModalState.groupFiles];
                    
                    // Show the group files modal again
                    this.groupFilesModal.show();
                }
            },
        },
        watch: {
            selectedFiles(newValue, oldValue) {
                // Intentionally empty - keep track of selected files
            },
            // Watch for file selection changes relevant to plotting
            selectedFileId(newFileId, oldFileId) {
                if (newFileId !== oldFileId) {
                    this.plotMarkerOptions = []; // Clear old options
                    this.plotChannelOptions = [];
                    this.selectedPlotDetails = null; // Also reset plot details
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
                    this.selectedPlotDetails = this.availablePlots.find(p => p.name === newPlotName) || null;
                    this.clearPlot();
                    // Selectors will be shown/hidden by computed props and v-if
                    // Population will be triggered by the showMarker/ChannelSelector watchers if needed
                }
            },
            // Watcher to populate marker select when it becomes visible
            showMarkerSelector(isVisible) {
                if (isVisible) {
                    // Use nextTick to ensure the element is in the DOM after v-if becomes true
                    this.$nextTick(() => {
                        this.populateMarkerSelect();
                    });
                }
            },
            // Watcher to populate channel select when it becomes visible
            showChannelSelector(isVisible) {
                if (isVisible) {
                    // Use nextTick to ensure the element is in the DOM after v-if becomes true
                     this.$nextTick(() => {
                        this.populateChannelSelect();
                    });
                }
            }
        },
        mounted() {
            // Initialize Bootstrap components after the Vue instance is mounted
            this.$nextTick(() => {
                this.initializeComponents();
                
                // Load classifications for both the search filters and hierarchy data
                this.loadClassifications();
                
                // Load hierarchy data - load all trials on startup
                this.loadHierarchyClassifications()
                  .then(() => this.loadAllSubjects())
                  .then(() => this.loadAllSessions())
                  .then(() => this.loadAllTrials())
                  .catch(error => {
                    console.error("Error loading initial hierarchy data:", error);
                    this.showNotification("Error loading existing data. Please refresh the page.", "danger");
                  });
                
                // Also perform an initial search to show existing files
                this.searchFiles();
                
                // Load analyses data
                this.loadAnalyses();
                
                // Load groups for the groups tab
                this.loadGroups();
                
                // Load plot options for the plot tab
                this.loadAvailablePlots();
                
                // Initialize tooltips
                const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
                [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
            });
        }
    });
});