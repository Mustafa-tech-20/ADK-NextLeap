import asyncio
from google.adk.artifacts import InMemoryArtifactService
from google.genai.types import Part


async def test():
   svc = InMemoryArtifactService()
   #svc.artifacts.clear()


   # Save one artifact
   await svc.save_artifact(
       app_name="solo",
       user_id="u1",
       session_id="s2",
       filename="tester1.txt",
       artifact=Part.from_bytes(data=b"solo data!", mime_type="text/plain"),
   )




   # Load it
   result = await svc.load_artifact(
       app_name="solo",
       user_id="u1",
       session_id="s2",
       filename="tester1.txt",
   )


   # Normalize to list
   if result is None:
       parts = []
   elif isinstance(result, list):
       parts = result
   else:
       parts = [result]


   print(f"Versions saved: {len(parts)}")
   for idx, p in enumerate(parts):
       print(f"Version {idx}: {p}")
       if hasattr(p, "data"):
           print("  data:", p.data, "=>", p.data.decode())
   print("All artifact keys in service:")
   for key in svc.artifacts.keys():
       print("  -", key)       
  


asyncio.run(test())



