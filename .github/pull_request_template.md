# Description

Please include a summary of the change and which issue is fixed. Please also include relevant motivation and context. List any dependencies that are required for this change.

Fixes # (issue)

## Type of change

Please delete options that are not relevant.

- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)

# How Has This Been Tested?

Please describe the tests that you ran to verify your changes. Provide instructions so we can reproduce. Please also list any relevant details for your test configuration

- [ ] Test A
- [ ] Test B

**Test Configuration**:
* Firmware version:
* Hardware:
* Toolchain:
* SDK:

# Checklist:

- [ ] My code follows the style guidelines of this project
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code, particularly in hard-to-understand areas

## Checklist for Models

If you added new models / made changes to exsting models, please fill this checklist. 

- [ ] The primary key of the Model is an AutoField
- [ ] I have defined the `__str__` method for the Model
- [ ] If the field is optional, it has been spcified explicitly
- [ ] I have added a `verbose_name` for each Field.
- [ ] I have added a docstring for the Model
- [ ] The model is registered on Admin Site.
- [ ] I have pushed the migrations.

## Checklist for API

If you added new api endpoints / made changes to exsting endpoints, please fill this checklist. 

- [ ] The endpoint is accessible through Swagger.
- [ ] The endpoint supports permissions and authentication for different roles.
- [ ] All exceptions have been handled and appropriate status code is returned to the user.
- [ ] I have added docstrings for ViewSets / Serializers.
