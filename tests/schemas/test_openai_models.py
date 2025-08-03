from __future__ import annotations

import os
import sys
import time

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..", "src")))

from ai_gateway.schemas.openai_models import (
    ListResponse,
    Model,
    ModelPermission,
)


def test_model_permission_valid() -> None:
    """Test valid ModelPermission creation."""
    perm = ModelPermission(
        id="perm-123",
        created=int(time.time()),
        allow_create_engine=False,
        allow_sampling=True,
        allow_logprobs=False,
        allow_search_indices=False,
        allow_view=True,
        allow_fine_tuning=False,
        organization=None,
        group=None,
        is_blocking=False,
    )
    assert perm.id == "perm-123"
    assert perm.object == "model_permission"
    assert perm.allow_create_engine is False
    assert perm.allow_sampling is True
    assert perm.is_blocking is False


def test_model_permission_rejects_empty_id() -> None:
    """Test ModelPermission rejects empty ID."""
    with pytest.raises(Exception):
        ModelPermission(
            id="  ",
            created=int(time.time()),
            allow_create_engine=False,
            allow_sampling=True,
            allow_logprobs=False,
            allow_search_indices=False,
            allow_view=True,
            allow_fine_tuning=False,
            is_blocking=False,
        )


def test_model_permission_created_validation() -> None:
    """Test ModelPermission created field validation."""
    now = int(time.time())

    # Valid cases
    perm1 = ModelPermission(
        id="perm-1",
        created=now,
        allow_create_engine=False,
        allow_sampling=True,
        allow_logprobs=False,
        allow_search_indices=False,
        allow_view=True,
        allow_fine_tuning=False,
        is_blocking=False,
    )
    assert perm1.created == now

    # Invalid cases
    with pytest.raises(Exception):
        ModelPermission(
            id="perm-2",
            created=-1,
            allow_create_engine=False,
            allow_sampling=True,
            allow_logprobs=False,
            allow_search_indices=False,
            allow_view=True,
            allow_fine_tuning=False,
            is_blocking=False,
        )

    with pytest.raises(Exception):
        ModelPermission(
            id="perm-3",
            created=1.5,  # type: ignore[arg-type]
            allow_create_engine=False,
            allow_sampling=True,
            allow_logprobs=False,
            allow_search_indices=False,
            allow_view=True,
            allow_fine_tuning=False,
            is_blocking=False,
        )


def test_model_valid() -> None:
    """Test valid Model creation."""
    now = int(time.time())
    perm = ModelPermission(
        id="perm-123",
        created=now,
        allow_create_engine=False,
        allow_sampling=True,
        allow_logprobs=False,
        allow_search_indices=False,
        allow_view=True,
        allow_fine_tuning=False,
        is_blocking=False,
    )

    model = Model(
        id="model-123",
        created=now,
        owned_by="ai_gateway",
        permission=[perm],
        root=None,
        parent=None,
    )
    assert model.id == "model-123"
    assert model.object == "model"
    assert model.owned_by == "ai_gateway"
    assert len(model.permission) == 1
    assert model.permission[0] == perm


def test_model_rejects_empty_fields() -> None:
    """Test Model rejects empty ID and owned_by."""
    now = int(time.time())
    perm = ModelPermission(
        id="perm-123",
        created=now,
        allow_create_engine=False,
        allow_sampling=True,
        allow_logprobs=False,
        allow_search_indices=False,
        allow_view=True,
        allow_fine_tuning=False,
        is_blocking=False,
    )

    # Empty ID
    with pytest.raises(Exception):
        Model(
            id="  ",
            created=now,
            owned_by="ai_gateway",
            permission=[perm],
        )

    # Empty owned_by
    with pytest.raises(Exception):
        Model(
            id="model-123",
            created=now,
            owned_by="  ",
            permission=[perm],
        )


def test_model_permission_list_validation() -> None:
    """Test Model permission list validation."""
    now = int(time.time())

    # Valid non-empty list
    perm = ModelPermission(
        id="perm-123",
        created=now,
        allow_create_engine=False,
        allow_sampling=True,
        allow_logprobs=False,
        allow_search_indices=False,
        allow_view=True,
        allow_fine_tuning=False,
        is_blocking=False,
    )

    model = Model(
        id="model-123",
        created=now,
        owned_by="ai_gateway",
        permission=[perm],
    )
    assert len(model.permission) == 1

    # Empty list should fail
    with pytest.raises(Exception):
        Model(
            id="model-123",
            created=now,
            owned_by="ai_gateway",
            permission=[],
        )


def test_model_created_validation() -> None:
    """Test Model created field validation."""
    now = int(time.time())
    perm = ModelPermission(
        id="perm-123",
        created=now,
        allow_create_engine=False,
        allow_sampling=True,
        allow_logprobs=False,
        allow_search_indices=False,
        allow_view=True,
        allow_fine_tuning=False,
        is_blocking=False,
    )

    # Valid case
    model = Model(
        id="model-123",
        created=now,
        owned_by="ai_gateway",
        permission=[perm],
    )
    assert model.created == now

    # Invalid cases
    with pytest.raises(Exception):
        Model(
            id="model-123",
            created=-1,
            owned_by="ai_gateway",
            permission=[perm],
        )

    with pytest.raises(Exception):
        Model(
            id="model-123",
            created=1.5,  # type: ignore[arg-type]
            owned_by="ai_gateway",
            permission=[perm],
        )


def test_list_response_valid() -> None:
    """Test valid ListResponse creation."""
    now = int(time.time())
    perm = ModelPermission(
        id="perm-123",
        created=now,
        allow_create_engine=False,
        allow_sampling=True,
        allow_logprobs=False,
        allow_search_indices=False,
        allow_view=True,
        allow_fine_tuning=False,
        is_blocking=False,
    )

    model1 = Model(
        id="model-1",
        created=now,
        owned_by="ai_gateway",
        permission=[perm],
    )

    model2 = Model(
        id="model-2",
        created=now,
        owned_by="ai_gateway",
        permission=[perm],
    )

    response = ListResponse[Model](data=[model1, model2])
    assert response.object == "list"
    assert len(response.data) == 2
    assert response.data[0] == model1
    assert response.data[1] == model2


def test_list_response_rejects_empty_data() -> None:
    """Test ListResponse rejects empty data."""
    with pytest.raises(Exception):
        ListResponse[Model](data=[])
