# Automations

Three things people use a cooker's app for, done by Home Assistant instead, so they keep working
with the app gone and the cooker's internet access blocked. None of them can start the heat, and
none of them raises it.

They use the entity ids this integration makes for a cooker named **Induction Cooker**. If yours
has another name, change the ids to match. Paste each one into a new automation or script in YAML
mode. They have been checked against Home Assistant's own validation, not run on a real cooker.

## A message when a cook ends

When the cooker goes from cooking or paused to idle or off. That includes its own timer running
out, a press on its button, a pause left for ten minutes (the cooker then switches itself off) and
**Stop** in Home Assistant.

```yaml
alias: Cooker finished
triggers:
  - trigger: state
    entity_id: sensor.induction_cooker_status
    from: [cooking, timing, paused]
    to: [idle, "off"]
actions:
  - action: notify.notify
    data:
      message: The cooker has finished.
```

`notify.notify` goes to every notifier you have. Use your phone's own, such as
`notify.mobile_app_<your_phone>`, to send it to one.

## Stop after a set time

A script. Run it, then press start on the cooker: it waits up to ten minutes for the heat to come
on, counts the minutes from then, and presses **Stop**. If the cook has already ended by then it
does nothing. Running it again starts the count afresh.

```yaml
alias: Cooker stop after
mode: restart
fields:
  minutes:
    name: Minutes
    required: true
    selector:
      number:
        min: 1
        max: 240
sequence:
  - wait_template: "{{ is_state('binary_sensor.induction_cooker_heating', 'on') }}"
    timeout: "00:10:00"
    continue_on_timeout: false
  - delay:
      minutes: "{{ minutes }}"
  - condition: state
    entity_id: sensor.induction_cooker_status
    state: [cooking, timing, paused]
  - action: button.press
    target:
      entity_id: button.induction_cooker_stop
```

The minutes keep counting through a pause.

## A warning when it's been left on

```yaml
alias: Cooker left on
triggers:
  - trigger: state
    entity_id: binary_sensor.induction_cooker_heating
    to: "on"
    for: "02:00:00"
actions:
  - action: notify.notify
    data:
      message: The cooker has been heating for two hours.
```

Two hours suits a stock or a hotpot. Pick your own. To have it stop the cook as well, add a
`button.press` on `button.induction_cooker_stop` after the message.
