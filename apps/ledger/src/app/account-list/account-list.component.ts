import { Component, OnInit } from '@angular/core';
import { LedgerService } from '../ledger.service';
import { Account } from '../models/account';

@Component({
  selector: 'app-account-list',
  templateUrl: './account-list.component.html',
  styleUrls: ['./account-list.component.css']
})
export class AccountListComponent {
    accounts: Account[] = [];
    singularResourceName: string;

    constructor(
        private ledgerService: LedgerService
    ) {
        this.singularResourceName = 'account';
    }

    ngOnInit() {
        this.ledgerService.getAccounts().subscribe(
            (accounts: Account[]) => this.accounts = accounts,
            (err: any) => console.log(err),
            () => console.log('All done getting accounts')
        );
    }
}
