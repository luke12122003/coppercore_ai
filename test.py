input_path = r'C:\CopperCoreAI\media\geospatial_datasets\Test_401\TMI_1089_1.tif'
print('geospatial_datasets\\' + input_path.split('geospatial_datasets\\')[-1])
<!-- <form method="post" action="{% url 'project_delete' project.id %}" style="display:inline;"> -->


<!-- Modal for Project Creation -->
<div class="modal fade" id="projectModal" tabindex="-1" aria-labelledby="projectModalLabel" aria-hidden="true">
    <div class="modal-dialog modal-lg modal-dialog-centered">
        <div class="modal-content" style="border-radius: 18px;">
            <div class="modal-header" style="background: #23262b; color: #fff; border-top-left-radius: 18px; border-top-right-radius: 18px;">
                <h5 class="modal-title" id="projectModalLabel">
                    <span class="material-icons align-middle" style="font-size: 1.6rem; vertical-align: middle;">add_circle</span>
                    Create New Project
                </h5>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
            </div>
            <div class="modal-body" style="background: #f1f5f8e7;">
                <form hx-post="{% url 'project_create' %}" hx-target="#project-list" hx-swap="innerHTML" enctype="multipart/form-data" autocomplete="off">
                    {% csrf_token %}
                    <div class="row g-3">
                        <div class="col-md-6">
                            <label for="name" class="form-label fw-bold">Project Name <span class="text-danger">*</span></label>
                            <input type="text" class="form-control" id="name" name="name" required>
                        </div>
                        <div class="col-md-6">
                            <label for="project_code" class="form-label fw-bold">Project Code</label>
                            <input type="text" class="form-control" id="project_code" name="project_code">
                        </div>
                        <div class="col-md-12">
                            <label for="description" class="form-label fw-bold">Description</label>
                            <textarea class="form-control" id="description" name="description" rows="2"></textarea>
                        </div>
                        <div class="col-md-6">
                            <label for="project_status" class="form-label fw-bold">Project Status</label>
                            <select class="form-select" id="project_status" name="project_status">
                                <option value="Planned">Planned</option>
                                <option value="Active">Active</option>
                                <option value="Completed">Completed</option>
                                <option value="Archived">Archived</option>
                            </select>
                        </div>
                        <div class="col-md-6">
                            <label for="country" class="form-label fw-bold">Country <span class="text-danger">*</span></label>
                            <input type="text" class="form-control" id="country" name="country" required>
                        </div>
                        <div class="col-md-6">
                            <label for="region" class="form-label fw-bold">Region <span class="text-danger">*</span></label>
                            <input type="text" class="form-control" id="region" name="region" required>
                        </div>
                        <div class="col-md-6">
                            <label for="target_minerals" class="form-label fw-bold">Target Minerals</label>
                            <input type="text" class="form-control" id="target_minerals" name="target_minerals" placeholder="Comma-separated list">
                        </div>
                        <div class="col-md-6">
                            <label for="mineral_type" class="form-label fw-bold">Mineral Type</label>
                            <input type="text" class="form-control" id="mineral_type" name="mineral_type">
                        </div>
                    </div>
                    <div class="modal-footer d-flex justify-content-end gap-2"
                         style="border-bottom-right-radius: 18px; border-bottom-left-radius: 18px; background: #f1f5f8e7;">
                        <button type="submit" class="btn btn-primary px-4">Create Project</button>
                        <button type="button" class="btn btn-secondary px-4" data-bs-dismiss="modal">Cancel</button>
                    </div>
                </form>
            </div>
        </div>
    </div>
</div>
{% endblock %}