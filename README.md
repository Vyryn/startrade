# Startrade
Startrade is an advanced roleplay community with a a discord server and a custom bot built from the ground up. Endless player opportunities and an emergent economy, as well as effective server moderation and general task automation are just a few of the goals of Startrade.
You can join the community here: 
https://discord.gg/vcCyNFt


#Features:
- Automated economy with multiple ways of earning income
- Buy and sell dozens of commodities across dozens of locations
- Monitor and reward user activity, ignoring spam with smart techniques
- Detailed and customizable permissioning
- Moderation assistance
- Rule enforcement


#Detailed Features:
- Monitor activity and provide 'activity points' based on message complexity, pace and word variety instead of simply number of messages sent
- Assign members a 'Verified' role upon acceptance of the rules in order to gain access to the server
- Add each member to a database upon registration to keep track of personal money, investments and inventory
- Create new items and register new locations with a command, saving them to the database
- Edit and remove items and locations with commands
- Shop browse command:
    - Browse by category
    - Browse all items
    - Show details and image of a specific item
    - Fuzzy matching
- Buy and sell commodities at different prices depending on location
    - Allow players to transfer to a new channel after reaching sufficient chat activity in the previous one to prevent spam, command to travel to a new channel
    - Different locations have fully configurable buy and sell prices, and may not buy or sell everything
    - Prices vary even at the same location slightly from moment to moment
    - Commands to view all possible buys and sells that you can afford, or below a given price
    - Pull list of locations and buy and sell prices from a google sheet using the google api, to allow comfortable editing of these values
- Invest money in a non-withdrawable account for small % returns over time, automatic configurable payouts on the hour
- Top command to list users by money, invested money, or activity
- Nuanced dice rolling command
    - Roll one die or a hundred thousand; specifiy number of dice or not, specify number of sides or not
    - Configurable defaults
    - Change display results depending on number of dice rolled
    - Display automatically tallied total when rolling more than one die
    - In the command specify meaning for die rolls, that is then mapped onto the results
- Commands to check your balance, send others money, buy and sell items, view your items
- Remind users arbitrary messages on request, and remind other users
- Emoji polls
- Custom permissions system with Authorization levels 1-10 for management commands
    - Commands to check and update member authorization, list all authorized members, etc.
- Ignore Channels
- Log all server messages and embeds to organized log files
- Log message edits and deletions, including bulk deletions, to a logging channel
- Time, echo and ping commands, commands to message a user, change playing status
- Configurable server prefix that can vary from server to server
- A 'viral' Certified Literate role: May be assigned by anyone with the role and indicates a high quality of roleplay. There is an automatically assigned currency reward for achieving this, and appropriate logging.
- Bot management commands: List users, direct database query, evaluate code snippet, delete single message by id, add an item to a user, add money to a user, distribute investment payouts on demand in addition to automatically, edit a bot message, delete multiple messages, kick ban or unban a member, or remove all the pins in a channel. 
- Load, unload and reload modules to change functionality without going offline