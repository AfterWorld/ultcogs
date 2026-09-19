# RepoHelp

Repository navigation for the bot's existing `[p]help` command. Requires Red 3.5.24+.

```
[p]repo update ultcogs
[p]cog install ultcogs repohelp
[p]load repohelp
[p]help
```

Use the name you assigned the repository if it is not `ultcogs`. Loading activates
this formatter immediately. If another custom formatter is active, loading fails
with an explanation; unload the other help cog first. `[p]unload repohelp` restores
standard help unless another formatter has taken over in the meantime.

Select a repository, then a cog, then a command. Command selection sends Red's
native detailed help in the original help context. Direct help, including
`[p]help staffapp setup`, continues to use Red's native formatter. Command groups
include their subcommands there. This cog does not add a slash help command.

Downloader metadata supplies repository names; only loaded cogs with visible,
usable commands appear. Red's bundled commands are under **Red Core**. Manually
installed cogs, deleted repository records, or unavailable Downloader metadata go
under **Local / Unknown Source**. No GitHub requests or credentials are needed.
Repo names use the local names assigned when adding repositories.

Menus show ten entries per page and support Home, Back, Previous and Next. Only
the invoking member can navigate their menu. Listings refresh and check current
member permissions at each interaction; hidden, disabled and unavailable commands
are excluded, regardless of more permissive standard help settings. Direct detailed
help continues to honor Red's own help settings. Unloaded cogs disappear on refresh.

The menu uses text when embeds are disabled and honors Red's DM-only help setting
(max pages in guild = 0). Other native pagination settings govern detailed help;
the repository browser uses its own buttons and a three-minute inactivity timeout.
On timeout, controls are removed where possible. Unloading stops existing menus;
old visible controls can remain but no longer function. Run help again after reload.

Tests cover grouping, pagination, current permissions, navigation, direct help,
formatter conflicts, unload behavior, missing metadata and text/DM output.
