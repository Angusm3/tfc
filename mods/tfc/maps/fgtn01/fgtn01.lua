-- Shot Down. Ported from the fgtn mission script (OpenRA 20140722 Lua API), then to the 20141029 API, now to the 20250330 API.
ScoutType = "sniper"
Scout2Type = "sniperd"
CameraDelay = 125
HijackerType = "hjkr"
MilitiaType = "cmbt"
ViceroidType = "vice"

-- Briefly create a scout at a waypoint to uncover the shroud there.
RevealAt = function(cell)
	local vision = Actor.Create(Scout2Type, true, { Location = cell, Owner = player })
	vision.Destroy()
end

RunInitialActivities = function()
	Camera.Position = Zelenkov.CenterPosition
	RevealAt(HijackerSpawn1.Location)
end

VillageAttackersKilled = function()
	CreateHijacker1()
end

V2AKilled = function()
	CreateMilitia1()
end

GuardsKilled = function()
	GetViceroids()
end

CreateHijacker1 = function()
	hijacker1 = Actor.Create(HijackerType, true, { Location = HijackerSpawn1.Location, Owner = player })
	hijacker1.Scatter()
	RevealAt(Vision2.Location)
	RevealAt(militiaspawn1.Location)
end

CreateMilitia1 = function()
	militia1 = Actor.Create(MilitiaType, true, { Location = militiaspawn1.Location, Owner = player })
	militia1.Scatter()
	militia2 = Actor.Create(MilitiaType, true, { Location = militiaspawn2.Location, Owner = player })
	militia2.Scatter()
end

GetViceroids = function()
	Vicef1.Destroy()
	Vicef2.Destroy()
	Vicef3.Destroy()
	Vicef4.Destroy()
	vice1 = Actor.Create(ViceroidType, true, { Location = Vicep1.Location, Owner = player })
	vice2 = Actor.Create(ViceroidType, true, { Location = Vicep2.Location, Owner = player })
	vice3 = Actor.Create(ViceroidType, true, { Location = Vicep3.Location, Owner = player })
	vice4 = Actor.Create(ViceroidType, true, { Location = Vicep4.Location, Owner = player })
end

-- Not called by the original script either (the mission defines no objectives yet).
MissionAccomplished = function()
	Media.DisplayMessage(UserInterface.GetFluentMessage("mission-accomplished"))
end

MissionFailed = function()
	Media.PlayMovieFullscreen("bmap.vqa")
end

WorldLoaded = function()
	player = Player.GetPlayer("Forgotten")

	Trigger.OnAllKilled({ VillageAttacker1, VillageAttacker2, VillageAttacker3, VillageAttacker4 }, VillageAttackersKilled)
	Trigger.OnAllKilled({ V2A1, V2A2, V2A3, V2A4 }, V2AKilled)
	Trigger.OnAllKilled({ Guard1, Guard2, Guard3, Guard4, Guard5, Guard6, Guard7, Guard8, Guard9 }, GuardsKilled)

	RunInitialActivities()
end
