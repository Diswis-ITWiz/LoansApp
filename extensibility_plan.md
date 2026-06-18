# Extensibility Plan For Item Types And Penalty Strategies

This plan describes the steps needed to make the application easier to extend when adding new item types, due-date rules, overdue rules, or penalty strategies.

## Current State

The application is already more extensible than the original version because item, overdue, return, and penalty behavior has been moved into service modules.

However, the current implementation still assumes two main item types:

- Type A
- Type B

Several services still use direct branching such as:

```python
if item_type == ItemType.A:
    ...
else:
    ...
```

This is acceptable for two item types, but it becomes harder to maintain if the system needs Type C, Type D, special penalty rules, grace periods, or different reminder behavior.

## Goal

Move item-specific behavior into explicit policy classes so each item type owns its own rules.

Each item type policy should be responsible for:

- Calculating the loan due date.
- Calculating overdue values.
- Calculating the penalty description.
- Applying penalty changes to the client.
- Selecting the return form.
- Preparing return assessment data.
- Supporting future email/reminder behavior if needed.

## Step 1: Add Characterization Tests Before Changing Behavior

Add or expand tests that lock in current behavior before refactoring.

Cover:

- Type A due-date behavior.
- Type B due-date behavior.
- Type A overdue calculation.
- Type B overdue calculation.
- Type A penalty thresholds.
- Type B penalty thresholds.
- Return completion for Type A.
- Return completion for Type B.
- Management command behavior for overdue email reminders.

Expected files:

- `base/tests/test_helpers.py`
- `base/tests/test_workflows.py`
- `base/tests/test_management_commands.py`
- Optional new file: `base/tests/test_item_policies.py`

## Step 2: Define A Common Item Policy Interface

Create a new module:

```text
base/services/item_policies.py
```

Define a base policy shape. This can be a normal class or an abstract base class.

Suggested methods:

```python
class ItemPolicy:
    item_type = None

    def calculate_due_date(self, client, item, loaned_at=None):
        raise NotImplementedError

    def calculate_overdue(self, due_date, client):
        raise NotImplementedError

    def calculate_penalty(self, overdue, client):
        raise NotImplementedError

    def apply_penalty(self, overdue, client):
        raise NotImplementedError

    def get_return_form_class(self):
        raise NotImplementedError

    def get_return_initial_data(self, transaction):
        raise NotImplementedError
```

Keep this interface small at first. Add methods only when the current code needs them.

## Step 3: Implement Type A And Type B Policies

Move Type A-specific behavior into a `TypeAItemPolicy`.

Move Type B-specific behavior into a `TypeBItemPolicy`.

Suggested classes:

```python
class TypeAItemPolicy(ItemPolicy):
    item_type = ItemType.A


class TypeBItemPolicy(ItemPolicy):
    item_type = ItemType.B
```

The first implementation can call the existing functions:

- `get_item_type_a_overdue_days`
- `get_item_type_b_overdue_time`
- `calculate_type_a_penalty`
- `calculate_type_b_penalty`
- `apply_type_a_penalty`
- `apply_type_b_penalty`

This keeps the first refactor low-risk.

## Step 4: Add A Policy Registry

Create a registry in `base/services/item_policies.py`.

Example:

```python
ITEM_POLICIES = {
    ItemType.A: TypeAItemPolicy(),
    ItemType.B: TypeBItemPolicy(),
}


def get_item_policy(item_type):
    return ITEM_POLICIES[item_type]
```

This lets the rest of the application ask for a policy instead of branching on item type.

## Step 5: Replace Return Workflow Branching

Refactor `base/services/returns.py`.

Replace logic like:

```python
if item_type == ItemType.A:
    ...
else:
    ...
```

With:

```python
policy = get_item_policy(item_type)
```

Then use the policy to:

- Calculate overdue values.
- Calculate penalties.
- Apply penalties.
- Prepare return initial data.
- Choose the correct return form.

This is the highest-value place to remove branching first.

## Step 6: Replace Loan Due-Date Branching

Refactor `base/services/loaning.py`.

Move Type A and Type B due-date behavior into the matching item policies.

The view should eventually call:

```python
policy = get_policy_for_item(item)
due_date = policy.calculate_due_date(client, item)
```

The existing `calculate_loan_due_date` function can remain temporarily as a compatibility wrapper.

## Step 7: Replace Penalty Function Branching

Refactor `base/services/penalties.py`.

Keep generic penalty helpers where useful, but move item-type-specific penalty thresholds and application behavior into policy classes.

After this step, adding a new penalty strategy should usually mean adding or changing one policy class instead of editing shared branching logic.

## Step 8: Update Views To Use Policy-Level Helpers

Update `base/views.py` so views do not need to know whether an item is Type A or Type B except for display purposes.

Targets:

- `loanItemTransaction`
- `returnItem2`
- `lateTranscactionDetails`

The view should delegate behavior to services/policies and only prepare the template context.

## Step 9: Update Forms If New Item Types Need Different Fields

Currently the app has separate return forms for Type A and Type B:

- `ReturnItemATransactionForm`
- `ReturnItemBTransactionForm`

If future item types need different return fields, the policy should expose the form class.

Example:

```python
form_class = policy.get_return_form_class()
```

This avoids adding more view-level `if item_type == ...` checks.

## Step 10: Update Email Reminder Commands

Review the email management commands:

- `senddeadlineemails`
- `sendoverdueitemaemails`
- `sendoverdueitembemails`

Options:

1. Keep separate commands per item type.
2. Replace them with one command that asks each policy whether a reminder should be sent.

The second option is more extensible but can be done later.

Suggested future design:

```python
for transaction in ongoing_transactions:
    policy = get_policy_for_item(transaction.itemCat)
    if policy.should_send_overdue_email(transaction):
        policy.send_overdue_email(transaction)
```

## Step 11: Add A New Item Type As A Trial

After Type A and Type B policies are working, add a small test-only or real Type C policy to prove the design.

This should require:

- Adding the new item type constant.
- Adding prefixes or classification rules.
- Adding one new policy class.
- Registering the policy.
- Adding tests.

If adding Type C still requires editing many unrelated files, the strategy extraction is not complete yet.

## Step 12: Keep Backwards Compatibility Wrappers Temporarily

Keep old service function names temporarily if tests or older code still import them.

Examples:

```python
calculateTypeAPenalty = calculate_type_a_penalty
applyTypeAPenalty = apply_type_a_penalty
```

Remove compatibility aliases only after the application and tests no longer depend on them.

## Step 13: Update Documentation

Update:

- `PROJECT_CONTEXT.md`
- `handover.md`
- `README.md` if setup or usage changes

Document how to add a new item type.

The documentation should include:

- Where item prefixes are registered.
- Where item type policies are registered.
- Which tests should be added.
- Whether email reminders need additional configuration.

## Suggested End State

Adding a new item type should require changes in only a small number of places:

1. Add the item type constant.
2. Add item prefix/name mapping.
3. Add a new item policy class.
4. Register the policy.
5. Add tests.

The target is to avoid editing `views.py` and avoid adding new `if item_type == ...` branches in shared services.
