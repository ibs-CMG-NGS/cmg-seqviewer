# FSM State Diagram

## States

```
┌─────────────┐
│    IDLE     │ ← Initial State
└──────┬──────┘
       │ LOAD_DATA
       ▼
┌─────────────┐
│ LOADING_    │
│    DATA     │
└──┬────┬─────┘
   │    │
   │    │ DATA_LOAD_FAILED
   │    └────────────────────┐
   │                         │
   │ DATA_LOAD_SUCCESS       │
   ▼                         ▼
┌─────────────┐         ┌──────────┐
│    DATA_    │         │  ERROR   │
│   LOADED    │         └────┬─────┘
└──┬──┬──┬───┘              │
   │  │  │                  │ ERROR_RESOLVED
   │  │  │                  │ or RESET
   │  │  │                  │
   │  │  │  ◄───────────────┘
   │  │  │
   │  │  │ START_FILTER
   │  │  ▼
   │  │ ┌──────────┐
   │  │ │FILTERING │
   │  │ └──┬───┬───┘
   │  │    │   │ FILTER_FAILED
   │  │    │   └─────────────────┐
   │  │    │                     │
   │  │    │ FILTER_SUCCESS      ▼
   │  │    ▼                 ┌────────┐
   │  │ ┌──────────┐         │ ERROR  │
   │  │ │ FILTER_  │         └────────┘
   │  │ │COMPLETE  │
   │  │ └──────────┘
   │  │
   │  │ START_ANALYSIS
   │  ▼
   │ ┌──────────┐
   │ │ANALYZING │
   │ └──┬───┬───┘
   │    │   │ ANALYSIS_FAILED
   │    │   └─────────────────┐
   │    │                     │
   │    │ ANALYSIS_SUCCESS    ▼
   │    ▼                 ┌────────┐
   │ ┌──────────┐         │ ERROR  │
   │ │ANALYSIS_ │         └────────┘
   │ │COMPLETE  │
   │ └──────────┘
   │
   │ START_COMPARISON
   ▼
┌──────────┐
│COMPARING │
└──┬───┬───┘
   │   │ COMPARISON_FAILED
   │   └─────────────────┐
   │                     │
   │ COMPARISON_SUCCESS  ▼
   ▼                 ┌────────┐
┌──────────┐         │ ERROR  │
│COMPARISON│         └────────┘
│ COMPLETE │
└──────────┘
```

## State Descriptions

### IDLE
- Initial state
- Waiting for user input
- **Allowed Transitions**: LOAD_DATA → LOADING_DATA

### LOADING_DATA
- Loading dataset from file
- Progress bar displayed
- **Allowed Transitions**: 
  - DATA_LOAD_SUCCESS → DATA_LOADED
  - DATA_LOAD_FAILED → ERROR

### DATA_LOADED
- Dataset successfully loaded
- Ready for operations
- **Allowed Transitions**:
  - START_FILTER → FILTERING
  - START_ANALYSIS → ANALYZING
  - START_COMPARISON → COMPARING
  - START_PLOT → PLOTTING
  - START_EXPORT → EXPORTING
  - LOAD_DATA → LOADING_DATA (load another dataset)

### FILTERING
- Applying filter criteria
- **Allowed Transitions**:
  - FILTER_SUCCESS → FILTER_COMPLETE
  - FILTER_FAILED → ERROR

### FILTER_COMPLETE
- Filtering completed successfully
- Results displayed in new tab
- **Allowed Transitions**:
  - START_FILTER → FILTERING (apply another filter)
  - START_ANALYSIS → ANALYZING
  - START_PLOT → PLOTTING
  - START_EXPORT → EXPORTING
  - RESET → DATA_LOADED

### ANALYZING
- Running statistical analysis (Fisher's, GSEA, etc.)
- **Allowed Transitions**:
  - ANALYSIS_SUCCESS → ANALYSIS_COMPLETE
  - ANALYSIS_FAILED → ERROR

### ANALYSIS_COMPLETE
- Analysis completed successfully
- Results displayed
- **Allowed Transitions**:
  - START_PLOT → PLOTTING
  - START_EXPORT → EXPORTING
  - RESET → DATA_LOADED

### COMPARING
- Comparing multiple datasets
- **Allowed Transitions**:
  - COMPARISON_SUCCESS → COMPARISON_COMPLETE
  - COMPARISON_FAILED → ERROR

### COMPARISON_COMPLETE
- Comparison completed successfully
- **Allowed Transitions**:
  - START_PLOT → PLOTTING
  - START_EXPORT → EXPORTING
  - RESET → DATA_LOADED

### PLOTTING
- Generating visualizations
- Child window displayed
- **Allowed Transitions**:
  - PLOT_COMPLETE → DATA_LOADED

### EXPORTING
- Exporting data to file
- **Allowed Transitions**:
  - EXPORT_COMPLETE → DATA_LOADED

### ERROR
- Error occurred during operation
- Error message displayed
- **Allowed Transitions**:
  - ERROR_RESOLVED → IDLE
  - RESET → IDLE

## Events

| Event | Description |
|-------|-------------|
| LOAD_DATA | Start loading dataset |
| DATA_LOAD_SUCCESS | Dataset loaded successfully |
| DATA_LOAD_FAILED | Failed to load dataset |
| START_FILTER | Start filtering operation |
| FILTER_SUCCESS | Filtering completed successfully |
| FILTER_FAILED | Filtering failed |
| START_ANALYSIS | Start statistical analysis |
| ANALYSIS_SUCCESS | Analysis completed successfully |
| ANALYSIS_FAILED | Analysis failed |
| START_COMPARISON | Start comparing datasets |
| COMPARISON_SUCCESS | Comparison completed successfully |
| COMPARISON_FAILED | Comparison failed |
| START_PLOT | Start generating plot |
| PLOT_COMPLETE | Plot generation complete |
| START_EXPORT | Start exporting data |
| EXPORT_COMPLETE | Export complete |
| RESET | Reset to previous stable state |
| ERROR_OCCURRED | Error occurred (from any state) |
| ERROR_RESOLVED | Error resolved |

## Usage in Code

```python
from core.fsm import FSM, State, Event

# Initialize FSM
fsm = FSM(initial_state=State.IDLE)

# Check if event can be triggered
if fsm.can_trigger(Event.LOAD_DATA):
    # Trigger event
    fsm.trigger(Event.LOAD_DATA)
    
# Check current state
print(f"Current state: {fsm.current_state.name}")

# Register callbacks
def on_data_loaded(**kwargs):
    print("Data loaded successfully!")

fsm.register_on_enter(State.DATA_LOADED, on_data_loaded)

# Add state change listener
def state_listener(old_state, new_state):
    print(f"State changed: {old_state.name} -> {new_state.name}")

fsm.add_state_change_listener(state_listener)
```
