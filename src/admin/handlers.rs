//! Admin API HTTP 处理器

use axum::{
    extract::{Path, State},
    http::StatusCode,
    response::IntoResponse,
    Json,
};

use super::{
    middleware::AdminState,
    types::{AdminErrorResponse, SetDisabledRequest, SetPriorityRequest, SuccessResponse},
};

/// GET /api/admin/credentials
/// 获取所有凭据状态
pub async fn get_all_credentials(State(state): State<AdminState>) -> impl IntoResponse {
    let response = state.service.get_all_credentials();
    Json(response)
}

/// POST /api/admin/credentials/:index/disabled
/// 设置凭据禁用状态
pub async fn set_credential_disabled(
    State(state): State<AdminState>,
    Path(index): Path<usize>,
    Json(payload): Json<SetDisabledRequest>,
) -> impl IntoResponse {
    match state.service.set_disabled(index, payload.disabled) {
        Ok(_) => {
            let action = if payload.disabled { "禁用" } else { "启用" };
            Json(SuccessResponse::new(format!("凭据 #{} 已{}", index, action))).into_response()
        }
        Err(e) => (
            StatusCode::BAD_REQUEST,
            Json(AdminErrorResponse::invalid_request(e.to_string())),
        )
            .into_response(),
    }
}

/// POST /api/admin/credentials/:index/priority
/// 设置凭据优先级
pub async fn set_credential_priority(
    State(state): State<AdminState>,
    Path(index): Path<usize>,
    Json(payload): Json<SetPriorityRequest>,
) -> impl IntoResponse {
    match state.service.set_priority(index, payload.priority) {
        Ok(_) => Json(SuccessResponse::new(format!(
            "凭据 #{} 优先级已设置为 {}",
            index, payload.priority
        )))
        .into_response(),
        Err(e) => (
            StatusCode::BAD_REQUEST,
            Json(AdminErrorResponse::invalid_request(e.to_string())),
        )
            .into_response(),
    }
}

/// POST /api/admin/credentials/:index/reset
/// 重置失败计数并重新启用
pub async fn reset_failure_count(
    State(state): State<AdminState>,
    Path(index): Path<usize>,
) -> impl IntoResponse {
    match state.service.reset_and_enable(index) {
        Ok(_) => Json(SuccessResponse::new(format!(
            "凭据 #{} 失败计数已重置并重新启用",
            index
        )))
        .into_response(),
        Err(e) => (
            StatusCode::BAD_REQUEST,
            Json(AdminErrorResponse::invalid_request(e.to_string())),
        )
            .into_response(),
    }
}

/// GET /api/admin/credentials/:index/balance
/// 获取指定凭据的余额
pub async fn get_credential_balance(
    State(state): State<AdminState>,
    Path(index): Path<usize>,
) -> impl IntoResponse {
    match state.service.get_balance(index).await {
        Ok(response) => Json(response).into_response(),
        Err(e) => (
            StatusCode::BAD_REQUEST,
            Json(AdminErrorResponse::api_error(e.to_string())),
        )
            .into_response(),
    }
}
