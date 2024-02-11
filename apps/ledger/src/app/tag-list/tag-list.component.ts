import { Component, OnInit } from '@angular/core';
import { LedgerService } from '../ledger.service';
import { Tag } from '../models/tag';
import { Router }  from '@angular/router';

@Component({
  selector: 'ledger-tag-list',
  templateUrl: './tag-list.component.html',
  styleUrls: ['./tag-list.component.css']
})
export class TagListComponent implements OnInit {
    tags: Tag[] = [];
    tagsLoaded: boolean = false;

    constructor(
        private ledgerService: LedgerService,
        private router: Router,
    ) {
    }

    ngOnInit() {
        this.ledgerService.getTags().subscribe(
            (tags: Tag[]) => this.tags = tags,
            (err: Error) => console.log(err),
            () => this.tagsLoaded = true,
        );
    }

    renameTag(event: Event, tag: Tag) {
        event.preventDefault();
        const promptResponse = prompt(`Rename ${tag} to:`);

        if (!promptResponse || promptResponse.trim() === '') {
            return;
        }

        const newTag = Tag.clone(tag);
        newTag.name = promptResponse.trim();

        this.ledgerService.renameTag(tag, newTag).subscribe({
            next: () => {
                this.ngOnInit();
            },
            error: (err: Error) => console.log(err),
        });
    }
}
