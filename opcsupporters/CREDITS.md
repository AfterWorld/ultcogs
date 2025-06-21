# Credits and Attribution

## Original Work by AAA3A

This cog is **heavily based on** and **inspired by** the original **ServerSupporters** cog created by **AAA3A**.

### Original Author Information
- **Developer**: AAA3A
- **GitHub**: https://github.com/AAA3A-AAA3A
- **Repository**: https://github.com/AAA3A-AAA3A/AAA3A-cogs
- **Original Cog**: ServerSupporters
- **License**: MIT License

### What We Borrowed from AAA3A's Original Work

#### Core Architecture & Logic (95% based on original)
- **Event Listeners**: `on_presence_update` and `on_member_update` structure
- **Caching System**: Anti-spam protection using `defaultdict(bool)` approach  
- **Change Detection**: Status tracking to only announce actual changes
- **Member Scanning**: Efficient pagination through large member lists
- **API Interaction**: Discord HTTP methods for clan tag detection
- **Error Handling**: Robust exception management throughout

#### Specific Code Patterns Adapted
- **Configuration System**: Guild-based config structure
- **Embed Design**: Color schemes, field layouts, and footer information
- **Regex Patterns**: Invite link detection in status messages
- **Permission Checks**: Admin/manage_guild permission requirements
- **Command Structure**: Hybrid command groups and subcommands

#### Original AAA3A Features We Maintained
```python
# These core concepts are directly from AAA3A's implementation:
- Smart member iteration with pagination
- Clan tag detection via Discord API
- Status activity parsing for custom activities  
- Cache-based spam prevention
- Change-only announcements
- Efficient bulk member scanning
- Robust error logging
```

### Our Modifications & Additions

#### What We Changed
- ❌ **Removed**: AAA3A_utils dependency (Settings, Menu, Cog classes)
- ❌ **Removed**: Role management functionality  
- ❌ **Removed**: Complex configuration options
- ✅ **Added**: Hardcoded OPC-specific values
- ✅ **Added**: Live statistics dashboard
- ✅ **Added**: Announcement-only functionality
- ✅ **Added**: Real-time supporter counts in embeds

#### Code We Wrote From Scratch
- Statistics counting and percentage calculations
- OPC-specific invite pattern matching
- Simplified configuration commands (`enabled`, `announcementchannel`)
- Custom embed layouts for announcements
- Supporter counting dashboard

### License Compliance

The original ServerSupporters cog by AAA3A is released under the **MIT License**, which allows:
- ✅ Commercial use
- ✅ Modification  
- ✅ Distribution
- ✅ Private use

**Requirements under MIT License:**
- ✅ **Include original license** (see LICENSE file)
- ✅ **Include copyright notice** (credited throughout code and documentation)

### Our Commitment to Attribution

We have ensured proper attribution by:
1. **Code Comments**: Every major function includes AAA3A attribution
2. **Documentation**: README prominently credits AAA3A's original work
3. **File Headers**: Credit comments in all source files
4. **Command Help**: Footer text mentions AAA3A's contribution
5. **This Credits File**: Detailed breakdown of what we borrowed vs. created

## Thank You AAA3A! 🙏

The One Piece Community server's supporter tracking system would not exist without AAA3A's excellent foundational work. Their original ServerSupporters cog provided:

- A robust, production-ready architecture
- Elegant solutions to complex Discord API challenges  
- Smart performance optimizations for large servers
- Clean, maintainable code patterns
- Comprehensive error handling

We encourage everyone to check out AAA3A's full collection of high-quality cogs at:
**https://github.com/AAA3A-AAA3A/AAA3A-cogs**

---

*This attribution document ensures full transparency about the origins of our cog's functionality and gives proper credit to the brilliant developer who made it possible.*