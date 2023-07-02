import { Component, OnInit, OnDestroy } from '@angular/core';
import { FormGroup, FormBuilder, Validators, AbstractControl } from '@angular/forms';
import { Router, ActivatedRoute, Params } from '@angular/router';
import { formatDate } from '@angular/common'
import { Account } from '../models/account';
import { AccountPrimitive } from '../types/accountPrimitive';
import { LedgerService } from '../ledger.service';
import { Observable, switchMap } from 'rxjs';
import { isObject, omitBy } from "lodash-es"


function dateRange(group: FormGroup): {[key: string]: boolean} | null {
    const openedOn = group.get('opened_on')!.value;
    const closedOn = group.get('closed_on')!.value;

    if (!closedOn) {
        return null;
    }

    if (closedOn >= openedOn) {
        return null;
    }

    return { 'daterange': true }
}

@Component({
  selector: 'app-account-form',
  templateUrl: './account-form.component.html',
  styleUrls: ['./account-form.component.css']
})
export class AccountFormComponent implements OnInit {
    accountForm!: FormGroup;
    account: Account | undefined;
    errorMessage = '';
    datesExpanded = false;
    singularResourceName: string;

    constructor(
        private router: Router,
        private route: ActivatedRoute,
        private formBuilder: FormBuilder,
        private ledgerService: LedgerService
    ) {
        this.singularResourceName = 'account';
    }

    ngOnInit(): void {
        const id = Number(this.route.snapshot.paramMap.get('id') || 0)

        this.accountForm = this.formBuilder.group({
            name: [null, {validators: [Validators.required]}],
            url: [null],
            dates: this.formBuilder.group({
                opened_on: this.today(),
                closed_on: null,
            }, {validators: dateRange}),
            note: [''],
        });

        this.ledgerService.getAccount(id).subscribe(
            (account: Account) => this.populate(account),
            (err: any) => console.log(err),
            () => console.log('All done getting account'),
        );
    }

    ngOnDestroy(): void {
    }

    get name() { return this.accountForm.controls['name'] }
    get dates() { return this.accountForm.controls['dates'] as FormGroup }
    get openedOn() { return this.dates.controls['opened_on'] }
    get closedOn() { return this.dates.controls['closed_on'] }
    get note() { return this.accountForm.controls['note'] }
    get url() { return this.accountForm.controls['url'] }

    today() {
        return formatDate(new Date(), 'yyyy-MM-dd', 'en');
    }

    save(): void {
        const primitive: AccountPrimitive = {
            uid: this.account!.uid,
            name: this.name.value,
            opened_on: this.openedOn.value || null,
            closed_on: this.closedOn.value || null,
            note: this.note.value,
            url: this.url.value,
        }

        if (primitive.uid === 0) {
            this.ledgerService.addAccount(primitive).subscribe(
                () => this.saved(),
                (err) => this.errorMessage = err,
            );
        }

        if (primitive.uid > 0) {
            this.ledgerService.updateAccount(primitive).subscribe(
                () => this.saved(),
                (err) => this.errorMessage = err,
            );
        }
    }

    saved() {
        this.accountForm.reset();
        this.router.navigate(['/accounts']);
    }

    deleted() {
        this.accountForm.reset();
        this.router.navigate(['/accounts']);
    }

    canDelete(): boolean {
        if (!this.account) {
            return false;
        }
        return this.account.uid > 0;
    }

    reset() {
        if (this.account) {
            this.populate(this.account);
        }
   }

    populate(account: Account) {
        this.accountForm.reset();

        this.accountForm.patchValue({
            name: account.name,
            url: account.url,
            dates: {
                opened_on: account.openedOnYMD(),
                closed_on: account.closedOnYMD(),
            },
            note: account.note,
        });

        this.account = account;
        this.datesExpanded = account.closed_on instanceof Date;
    }

    toggleAccountClosed(event: Event) {
        this.datesExpanded = (event.target as HTMLInputElement).checked;
        this.accountForm.markAsDirty();

        this.dates.patchValue({
            closed_on: (this.datesExpanded)? this.today() : null,
        });
    }

    deleteAccount() {
        if (!this.account) {
            return;
        }

        this.ledgerService.deleteAccount(this.account.uid).subscribe(
            () => this.deleted(),
            (err) => this.errorMessage = err,
        );
    }
}
