# def test_extra_state_attributes(mocked_coordinator):
#     model = "bean model"
#     device_id = "bean-123"
#     child_id = "bean-123-123"
#     test_fan = light.HubspaceLight(
#         mocked_coordinator,
#         "test light",
#         model=model,
#         device_id=device_id,
#         child_id=child_id,
#     )
#     assert test_fan.extra_state_attributes == {
#         "model": model,
#         "deviceId": device_id,
#         "Child ID": child_id,
#     }
