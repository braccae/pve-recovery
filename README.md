Hi yeah my proxmox cluster broke and I'm trying to fix it. There's no turnkey tools for this, so I'm making a helper script to make it easier.

Very WIP and kinda messy while I prototype

Non-exhaustive dependencies:
- python
- qemu-img
- lvm2
- guestmount
- libguestfs
- libguestfs-tools