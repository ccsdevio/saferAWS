resource "aws_api_gateway_rest_api" "test_api" {
  name = "test1"
}

resource "aws_api_gateway_resource" "test1resource1" {
  rest_api_id = aws_api_gateway_rest_api.cc_api.id
  parent_id   = aws_api_gateway_rest_api.cc_api.root_resource_id
  path_part   = "test1resource1"
}