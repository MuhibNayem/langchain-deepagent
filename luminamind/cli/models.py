"""CLI for model management in LuminaMind."""
import click
from luminamind.models.registry import ModelRegistry, AgentRole, RoleModelMapping
from luminamind.models.presets import ModelPresets


@click.group(name='models')
def models_group():
    """Manage model configurations."""
    pass


@models_group.command('list')
def list_models():
    """List all available models."""
    registry = ModelRegistry()
    click.echo("Role -> Model mappings:")
    for mapping in registry.list_all():
        status = "✓" if mapping.enabled else "✗"
        click.echo(f"  {status} {mapping.role.value}: {mapping.provider}/{mapping.model} "
                  f"(temp={mapping.temperature}, max_tokens={mapping.max_tokens})")


@models_group.command('set')
@click.option('--role', required=True,
              type=click.Choice(['planner', 'executor', 'evaluator', 'critic', 'orchestrator']))
@click.option('--provider', required=True, help="Provider name (e.g., openai, anthropic)")
@click.option('--model', required=True, help="Model name (e.g., gpt-4o, claude-3-haiku)")
@click.option('--temperature', default=0.7, type=float, help="Sampling temperature (0-2)")
@click.option('--max-tokens', default=4000, type=int, help="Maximum tokens to generate")
def set_model(role, provider, model, temperature, max_tokens):
    """Set model for a role."""
    registry = ModelRegistry()
    mapping = RoleModelMapping(
        role=AgentRole(role),
        provider=provider,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        enabled=True
    )
    registry.set(AgentRole(role), mapping)
    click.echo(f"Set {role} to {provider}/{model} (temp={temperature}, max_tokens={max_tokens})")


@models_group.command('preset')
@click.argument('preset_name')
def apply_preset(preset_name):
    """Apply a model preset."""
    presets = ModelPresets()
    preset = presets.get(preset_name)
    if not preset:
        click.echo(f"Unknown preset: {preset_name}")
        click.echo(f"Available presets: {', '.join(p.name for p in presets.list_presets())}")
        return

    registry = ModelRegistry()
    presets.apply_preset(preset_name, registry)
    click.echo(f"Applied preset: {preset_name}")
    click.echo(f"Description: {preset.description}")
    if preset.is_free_optimal:
        click.echo("(Free-optimal mode: using free models where possible)")


@models_group.command('presets')
def list_presets():
    """List all available model presets."""
    presets = ModelPresets()
    click.echo("Available presets:")
    for preset in presets.list_presets():
        free_tag = " [FREE-OPTIMAL]" if preset.is_free_optimal else ""
        click.echo(f"  {preset.name}{free_tag}")
        click.echo(f"    {preset.description}")
        for role, model_key in preset.mappings.items():
            click.echo(f"      {role}: {model_key}")


@models_group.command('get')
@click.option('--role', required=True,
              type=click.Choice(['planner', 'executor', 'evaluator', 'critic', 'orchestrator']))
def get_model(role):
    """Get model configuration for a role."""
    registry = ModelRegistry()
    mapping = registry.get(AgentRole(role))
    if mapping:
        click.echo(f"Role: {role}")
        click.echo(f"  Provider: {mapping.provider}")
        click.echo(f"  Model: {mapping.model}")
        click.echo(f"  Temperature: {mapping.temperature}")
        click.echo(f"  Max tokens: {mapping.max_tokens}")
        click.echo(f"  Enabled: {mapping.enabled}")
    else:
        click.echo(f"No configuration found for role: {role}")